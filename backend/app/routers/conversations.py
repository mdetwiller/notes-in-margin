from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..guide import guide_questions_in_order, resolve_guide
from ..models_cortico import Conversation, Participant, Snippet
from ..models_prototype import SectionCheckpoint, TranscriptState
from ..schemas import TranscriptStateUpdate

router = APIRouter(prefix="/conversations", tags=["conversations"])
config = get_config()


@router.get("")
def list_conversations(cortico_db: Session = Depends(get_cortico_db)):
    conversations = (
        cortico_db.query(Conversation)
        .filter(Conversation.id.in_(config.scoped_conversation_ids))
        .order_by(Conversation.id)
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "project_id": c.project_id,
            "duration_seconds": c.duration_seconds,
            "language": c.language,
            "audio_url": c.audio_url,
            "has_audio": bool(c.audio_url),
        }
        for c in conversations
    ]


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    conversation = cortico_db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "conversation not found")

    participants = {
        p.id: p
        for p in cortico_db.query(Participant).filter(Participant.conversation_id == conversation_id)
    }
    snippets = (
        cortico_db.query(Snippet)
        .filter(Snippet.conversation_id == conversation_id)
        .order_by(Snippet.order_index)
        .all()
    )
    snippet_payload = []
    for s in snippets:
        speaker = participants.get(s.participant_id)
        snippet_payload.append(
            {
                "snippet_id": s.id,
                "order_index": s.order_index,
                "speaker_name": speaker.name if speaker else None,
                "is_facilitator": bool(speaker.is_facilitator) if speaker else False,
                "start_offset": s.start_offset,
                "end_offset": s.end_offset,
                "text": s.text,
                "words": json.loads(s.words) if s.words else [],
            }
        )

    guide = resolve_guide(cortico_db, conversation)
    guide_questions = guide_questions_in_order(cortico_db, guide) if guide else []

    checkpoints = (
        prototype_db.query(SectionCheckpoint)
        .filter(
            SectionCheckpoint.user_id == config.default_user_id,
            SectionCheckpoint.conversation_id == conversation_id,
        )
        .all()
    )
    checkpoint_by_question = {c.guide_question_id: c for c in checkpoints}

    guide_payload = [
        {
            "guide_question_id": q.id,
            "text": q.text,
            "shorthand_code": q.shorthand_code,
            "order_index": q.order_index,
            "checkpoint_snippet_id": checkpoint_by_question[q.id].snippet_id
            if q.id in checkpoint_by_question
            else None,
        }
        for q in guide_questions
    ]

    state = prototype_db.get(TranscriptState, (config.default_user_id, conversation_id))

    return {
        "id": conversation.id,
        "title": conversation.title,
        "audio_url": conversation.audio_url,
        "has_audio": bool(conversation.audio_url),
        "duration_seconds": conversation.duration_seconds,
        "language": conversation.language,
        "snippets": snippet_payload,
        "guide_questions": guide_payload,
        "transcript_state": {
            "reached_end_at": state.reached_end_at.isoformat() if state and state.reached_end_at else None,
            "prompt_dismissed_at": state.prompt_dismissed_at.isoformat()
            if state and state.prompt_dismissed_at
            else None,
        },
    }


@router.put("/{conversation_id}/state")
def update_transcript_state(
    conversation_id: int,
    body: TranscriptStateUpdate,
    prototype_db: Session = Depends(get_prototype_db),
):
    state = prototype_db.get(TranscriptState, (config.default_user_id, conversation_id))
    if state is None:
        state = TranscriptState(user_id=config.default_user_id, conversation_id=conversation_id)
        prototype_db.add(state)

    now = datetime.now(timezone.utc)
    if body.reached_end_at:
        state.reached_end_at = now
    if body.prompt_dismissed is not None:
        state.prompt_dismissed_at = now if body.prompt_dismissed else None

    prototype_db.commit()
    return {
        "reached_end_at": state.reached_end_at.isoformat() if state.reached_end_at else None,
        "prompt_dismissed_at": state.prompt_dismissed_at.isoformat() if state.prompt_dismissed_at else None,
    }
