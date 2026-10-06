"""AI review: proposes RQ connections + evidence from a voice memo transcription.

Guardrails from the PRD: quote/point to the transcript and the user's own words, never
invent evidence; never state insights the user didn't voice; say so when a reflection
doesn't clearly connect to any RQ.

Validation (closes the PRD's open "how are outputs validated" question): every evidence
passage the model returns is checked structurally against the real conversation (snippet
exists, belongs to this conversation, indices in range) before it's ever shown to the user.
That check is the automated half; the human accept/edit/reject review step is the semantic
half — the PRD is explicit the AI never writes to the memo on its own.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import Config
from ..models_cortico import Participant, Snippet
from ..models_prototype import (
    AppSetting,
    ConnectionEvidence,
    ReflectionConnection,
    ResearchQuestion,
    RLHighlight,
    VoiceMemo,
)

DEFAULT_REVIEW_PROMPT = """You are helping a sensemaker file a spoken reflection into their \
running research-question (RQ) memo.

Rules:
- Only use what the user actually said in their reflection, or what the transcript actually \
contains. Never invent an insight the user did not voice.
- Quote or closely paraphrase the user's own words for each insight.
- For each connection, cite evidence as transcript passages (snippet id + word-index range). \
Starred highlights are always valid candidate evidence for their RQ, even if the reflection \
never mentions them.
- Prefer the user's own highlights over unhighlighted transcript text as evidence; you may \
propose additional unhighlighted passages, clearly marked as AI-suggested.
- A reflection may connect to several RQs, or none. If it doesn't clearly connect to any RQ, \
say so rather than forcing a connection.
- Separately extract any "what I'd like to hear next" statements as interests; do not propose \
new directions yourself.
- For each connection, also point to the word-index range *within the reflection transcription \
itself* that the insight was drawn from (reflection_quote_start_word/reflection_quote_end_word), \
so the memo can link straight to that moment in the recording. Leave both null only if you \
can't locate a specific span.
"""

REVIEW_PROMPT_SETTING_KEY = "review_prompt"


def get_review_prompt(prototype_db: Session) -> str:
    row = prototype_db.get(AppSetting, REVIEW_PROMPT_SETTING_KEY)
    return row.value if row else DEFAULT_REVIEW_PROMPT


def set_review_prompt(prototype_db: Session, text: str) -> None:
    row = prototype_db.get(AppSetting, REVIEW_PROMPT_SETTING_KEY)
    if row:
        row.value = text
    else:
        row = AppSetting(key=REVIEW_PROMPT_SETTING_KEY, value=text)
        prototype_db.add(row)
    prototype_db.commit()


def reset_review_prompt(prototype_db: Session) -> str:
    set_review_prompt(prototype_db, DEFAULT_REVIEW_PROMPT)
    return DEFAULT_REVIEW_PROMPT


_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "connections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "research_question_id": {"type": ["integer", "null"]},
                    "insight_text": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "rationale": {"type": "string"},
                    "reflection_quote_start_word": {"type": ["integer", "null"]},
                    "reflection_quote_end_word": {"type": ["integer", "null"]},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "snippet_id": {"type": "integer"},
                                "start_index": {"type": "integer"},
                                "end_index": {"type": "integer"},
                            },
                            "required": ["snippet_id", "start_index", "end_index"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "research_question_id",
                    "insight_text",
                    "confidence",
                    "rationale",
                    "reflection_quote_start_word",
                    "reflection_quote_end_word",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
        "extracted_interests": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["connections", "extracted_interests"],
    "additionalProperties": False,
}


def _build_transcript_context(cortico_db: Session, conversation_id: int) -> list[dict]:
    snippets = (
        cortico_db.query(Snippet)
        .filter(Snippet.conversation_id == conversation_id)
        .order_by(Snippet.order_index)
        .all()
    )
    participants = {
        p.id: p for p in cortico_db.query(Participant).filter(
            Participant.conversation_id == conversation_id
        )
    }
    out = []
    for s in snippets:
        speaker = participants.get(s.participant_id)
        out.append(
            {
                "snippet_id": s.id,
                "speaker": speaker.name if speaker else None,
                "is_facilitator": bool(speaker.is_facilitator) if speaker else False,
                "text": s.text,
                "word_count": len(json.loads(s.words)) if s.words else 0,
            }
        )
    return out


def _build_highlight_context(prototype_db: Session, user_id: int, conversation_id: int) -> list[dict]:
    highlights = (
        prototype_db.query(RLHighlight)
        .filter(RLHighlight.user_id == user_id, RLHighlight.conversation_id == conversation_id)
        .all()
    )
    return [
        {
            "highlight_id": h.id,
            "notes": h.notes,
            "starred": h.starred,
            "snippets": [
                {"snippet_id": hs.snippet_id, "start_index": hs.start_index, "end_index": hs.end_index}
                for hs in h.snippets  # type: ignore[attr-defined]
            ],
        }
        for h in highlights
    ]


def reflection_timestamp_from_words(
    transcription_raw: str | None, start_word: int | None
) -> float | None:
    """Looks up the audio offset (seconds) of a word index in the voice memo's own
    transcription, so a connection can link straight to the moment it was spoken rather
    than just the start of the recording. Returns None if unlocatable — the caller falls
    back to playing from the start."""
    if start_word is None or not transcription_raw:
        return None
    words = json.loads(transcription_raw)
    if not (0 <= start_word < len(words)):
        return None
    return words[start_word]["start"]


def _validate_evidence_in_range(
    cortico_db: Session, conversation_id: int, snippet_id: int, start_index: int, end_index: int
) -> bool:
    snippet = cortico_db.get(Snippet, snippet_id)
    if snippet is None or snippet.conversation_id != conversation_id:
        return False
    word_count = len(json.loads(snippet.words)) if snippet.words else 0
    return 0 <= start_index < end_index <= word_count


def generate_connections(
    *,
    prototype_db: Session,
    cortico_db: Session,
    voice_memo: VoiceMemo,
    config: Config,
) -> ReflectionConnection.__class__:
    """Calls the model, structurally validates its evidence, and persists every proposed
    connection with status='suggested' immediately (audit trail from the start — rejected
    proposals stay logged rather than deleted, per the PRD)."""

    transcription = voice_memo.transcription_edited or voice_memo.transcription_raw or ""
    research_questions = (
        prototype_db.query(ResearchQuestion)
        .filter(
            ResearchQuestion.user_id == voice_memo.user_id,
            ResearchQuestion.archived.is_(False),
        )
        .order_by(ResearchQuestion.display_order)
        .all()
    )
    prompt = get_review_prompt(prototype_db)

    reflection_word_count = len(json.loads(voice_memo.transcription_raw)) if voice_memo.transcription_raw else 0

    payload = {
        "reflection_transcription": transcription,
        "reflection_word_count": reflection_word_count,
        "research_questions": [
            {"id": rq.id, "name": rq.name, "description": rq.description} for rq in research_questions
        ],
        "transcript_snippets": _build_transcript_context(cortico_db, voice_memo.conversation_id),
        "user_highlights": _build_highlight_context(
            prototype_db, voice_memo.user_id, voice_memo.conversation_id
        ),
    }

    client = OpenAI()
    response = client.responses.create(
        model=config.ai_review.model,
        reasoning={"effort": config.ai_review.reasoning_effort},
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "reflection_review",
                "schema": _OUTPUT_SCHEMA,
                "strict": True,
            }
        },
    )
    result = json.loads(response.output_text)

    voice_memo.extracted_interests = json.dumps(result.get("extracted_interests", []))

    created: list[ReflectionConnection] = []
    for conn in result.get("connections", []):
        valid_evidence = []
        for ev in conn.get("evidence", []):
            if _validate_evidence_in_range(
                cortico_db, voice_memo.conversation_id, ev["snippet_id"], ev["start_index"], ev["end_index"]
            ):
                valid_evidence.append(ev)
            # else: dropped silently — hallucinated/out-of-range evidence never reaches review.

        reflection_timestamp = reflection_timestamp_from_words(
            voice_memo.transcription_raw, conn.get("reflection_quote_start_word")
        )

        connection = ReflectionConnection(
            voice_memo_id=voice_memo.id,
            research_question_id=conn.get("research_question_id"),
            insight_text=conn["insight_text"],
            source="ai",
            status="suggested",
            ai_metadata=json.dumps(
                {
                    "model": config.ai_review.model,
                    "reasoning_effort": config.ai_review.reasoning_effort,
                    "prompt": prompt,
                    "confidence": conn.get("confidence"),
                    "rationale": conn.get("rationale"),
                    "reflection_timestamp": reflection_timestamp,
                }
            ),
            created_at=datetime.now(timezone.utc),
        )
        prototype_db.add(connection)
        prototype_db.flush()  # assign connection.id

        starred_snippet_ids = {
            (ev["snippet_id"], ev["start_index"], ev["end_index"])
            for h in _build_highlight_context(
                prototype_db, voice_memo.user_id, voice_memo.conversation_id
            )
            if h["starred"]
            for ev in h["snippets"]
        }

        for ev in valid_evidence:
            key = (ev["snippet_id"], ev["start_index"], ev["end_index"])
            prototype_db.add(
                ConnectionEvidence(
                    connection_id=connection.id,
                    snippet_id=ev["snippet_id"],
                    start_index=ev["start_index"],
                    end_index=ev["end_index"],
                    source="user" if key in starred_snippet_ids else "ai",
                )
            )
        created.append(connection)

    prototype_db.commit()
    return created
