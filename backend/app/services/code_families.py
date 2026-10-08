"""Synthesizes thematic "code families" from a research question's filed memo entries — a
precursor to a future codebook/tagging system, not a replacement for one (per
docs/prd-phase-2.md: assigning codes to individual highlights/snippets stays out of scope
this round). Same human-in-the-loop posture as ai_review.py and next_steps.py: the model
proposes family definitions grounded in the user's own already-accepted/edited insights;
nothing is "decided" until the user accepts, renames, or dismisses.
"""
from __future__ import annotations

import json

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import Config
from ..evidence_text import quoted_texts
from ..models_prototype import CodeFamily, CodeFamilyMember, ReflectionConnection

FILED_STATUSES = ("accepted", "edited")

CODE_FAMILY_PROMPT = """You help a sensemaker build a first-draft codebook from their own \
already-filed research insights, one research question (RQ) at a time.

You are given every accepted/edited memo entry under this RQ (insight text plus the evidence \
passages behind it), and any thematic clusters ("code families") already proposed or accepted \
for this RQ.

Rules:
- Propose "code families": named, defined thematic clusters of the memo entries you were given. \
A family's definition must be grounded in the actual insight text/evidence you were given — \
don't invent a theme the entries don't support.
- Every value in member_connection_ids must be one of the connection ids you were actually \
given — never invent one.
- If an entry fits an existing family you were given, reference that family's existing_family_id \
instead of proposing a near-duplicate new family — only create a new family when nothing \
existing genuinely fits.
- This produces family *definitions* only — never propose assigning codes to individual \
highlights or snippets; that stays out of scope.
- It's fine to leave entries out of every family if they don't cluster with anything yet, and \
fine to return an empty families list if nothing genuinely clusters.
"""

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "existing_family_id": {"type": ["integer", "null"]},
                    "name": {"type": ["string", "null"]},
                    "definition": {"type": ["string", "null"]},
                    "member_connection_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["existing_family_id", "name", "definition", "member_connection_ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["families"],
    "additionalProperties": False,
}


def _filed_connections_for_rq(prototype_db: Session, research_question_id: int) -> list[ReflectionConnection]:
    return (
        prototype_db.query(ReflectionConnection)
        .filter(
            ReflectionConnection.research_question_id == research_question_id,
            ReflectionConnection.status.in_(FILED_STATUSES),
        )
        .all()
    )


def _valid_connection_ids(prototype_db: Session, research_question_id: int) -> set[int]:
    """Every member_connection_id the model proposes must resolve to one of these before
    it's trusted — mirrors next_steps._valid_conversation_ids."""
    rows = (
        prototype_db.query(ReflectionConnection.id)
        .filter(
            ReflectionConnection.research_question_id == research_question_id,
            ReflectionConnection.status.in_(FILED_STATUSES),
        )
        .all()
    )
    return {row.id for row in rows}


def _connection_context(cortico_db: Session, connections: list[ReflectionConnection]) -> list[dict]:
    spans = [(e.snippet_id, e.start_index, e.end_index) for c in connections for e in c.evidence]
    text_by_span = quoted_texts(cortico_db, spans)
    return [
        {
            "connection_id": c.id,
            "insight_text": c.insight_text,
            "evidence": [text_by_span.get((e.snippet_id, e.start_index, e.end_index), "") for e in c.evidence],
        }
        for c in connections
    ]


def _existing_families_context(
    prototype_db: Session, research_question_id: int
) -> tuple[list[CodeFamily], list[dict]]:
    families = (
        prototype_db.query(CodeFamily)
        .filter(CodeFamily.research_question_id == research_question_id, CodeFamily.status != "dismissed")
        .all()
    )
    return families, [
        {
            "id": f.id,
            "name": f.name,
            "definition": f.definition,
            "member_connection_ids": [m.connection_id for m in f.members],
        }
        for f in families
    ]


def _apply_family_results(
    prototype_db: Session,
    *,
    research_question_id: int,
    user_id: int,
    raw_families: list[dict],
    valid_connection_ids: set[int],
    existing_family_ids: set[int],
    ai_metadata: dict,
) -> list[CodeFamily]:
    touched: list[CodeFamily] = []
    for fam in raw_families:
        member_ids = [cid for cid in fam.get("member_connection_ids", []) if cid in valid_connection_ids]
        if not member_ids:
            continue  # nothing real left to attach for this candidate

        target: CodeFamily | None = None
        existing_id = fam.get("existing_family_id")
        if existing_id is not None and existing_id in existing_family_ids:
            target = prototype_db.get(CodeFamily, existing_id)

        if target is None:
            name = fam.get("name")
            definition = fam.get("definition")
            if not name or not definition:
                continue  # no existing family matched and nothing coherent to create
            target = CodeFamily(
                user_id=user_id,
                research_question_id=research_question_id,
                name=name,
                definition=definition,
                status="suggested",
                ai_metadata=json.dumps(ai_metadata),
            )
            prototype_db.add(target)
            prototype_db.flush()  # assign target.id

        existing_member_ids = {m.connection_id for m in target.members}
        for cid in member_ids:
            if cid not in existing_member_ids:
                prototype_db.add(CodeFamilyMember(code_family_id=target.id, connection_id=cid))
                existing_member_ids.add(cid)

        touched.append(target)

    prototype_db.commit()
    return touched


def synthesize_code_families(
    *,
    prototype_db: Session,
    cortico_db: Session,
    config: Config,
    user_id: int,
    research_question_id: int,
) -> list[CodeFamily]:
    connections = _filed_connections_for_rq(prototype_db, research_question_id)
    if not connections:
        return []  # nothing filed yet under this RQ — don't spend a call synthesizing nothing

    existing_families, existing_context = _existing_families_context(prototype_db, research_question_id)

    payload = {
        "memo_entries": _connection_context(cortico_db, connections),
        "existing_code_families": existing_context,
    }

    client = OpenAI()
    response = client.responses.create(
        model=config.ai_review.model,
        reasoning={"effort": config.ai_review.reasoning_effort},
        input=[
            {"role": "system", "content": CODE_FAMILY_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "code_families",
                "schema": _OUTPUT_SCHEMA,
                "strict": True,
            }
        },
    )
    result = json.loads(response.output_text)

    return _apply_family_results(
        prototype_db,
        research_question_id=research_question_id,
        user_id=user_id,
        raw_families=result.get("families", []),
        valid_connection_ids=_valid_connection_ids(prototype_db, research_question_id),
        existing_family_ids={f.id for f in existing_families},
        ai_metadata={
            "model": config.ai_review.model,
            "reasoning_effort": config.ai_review.reasoning_effort,
            "prompt": CODE_FAMILY_PROMPT,
        },
    )
