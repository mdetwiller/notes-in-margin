from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..guide import guide_questions_in_order, resolve_guide
from ..models_cortico import Conversation
from ..models_prototype import SectionCheckpoint
from ..schemas import CheckpointSet

router = APIRouter(prefix="/conversations/{conversation_id}/checkpoints", tags=["checkpoints"])
config = get_config()


@router.put("")
def set_checkpoint(
    conversation_id: int,
    body: CheckpointSet,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    conversation = cortico_db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "conversation not found")
    guide = resolve_guide(cortico_db, conversation)
    valid_question_ids = {q.id for q in guide_questions_in_order(cortico_db, guide)} if guide else set()
    if body.guide_question_id not in valid_question_ids:
        raise HTTPException(400, "guide_question_id is not part of this conversation's guide")

    # At most one checkpoint per guide question per conversation — moving replaces the old one.
    existing = (
        prototype_db.query(SectionCheckpoint)
        .filter(
            SectionCheckpoint.user_id == config.default_user_id,
            SectionCheckpoint.conversation_id == conversation_id,
            SectionCheckpoint.guide_question_id == body.guide_question_id,
        )
        .one_or_none()
    )
    if existing:
        existing.snippet_id = body.snippet_id
    else:
        prototype_db.add(
            SectionCheckpoint(
                user_id=config.default_user_id,
                conversation_id=conversation_id,
                guide_question_id=body.guide_question_id,
                snippet_id=body.snippet_id,
            )
        )
    prototype_db.commit()
    return {"guide_question_id": body.guide_question_id, "snippet_id": body.snippet_id}


@router.delete("/{guide_question_id}")
def delete_checkpoint(
    conversation_id: int, guide_question_id: int, prototype_db: Session = Depends(get_prototype_db)
):
    existing = (
        prototype_db.query(SectionCheckpoint)
        .filter(
            SectionCheckpoint.user_id == config.default_user_id,
            SectionCheckpoint.conversation_id == conversation_id,
            SectionCheckpoint.guide_question_id == guide_question_id,
        )
        .one_or_none()
    )
    if existing is None:
        raise HTTPException(404, "checkpoint not found")
    prototype_db.delete(existing)
    prototype_db.commit()
    return {"deleted": True}
