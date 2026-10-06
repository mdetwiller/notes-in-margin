from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..models_cortico import Conversation
from ..models_prototype import NextStepSuggestion
from ..services.next_steps import generate_next_step_suggestions

router = APIRouter(prefix="/next_steps", tags=["next_steps"])
config = get_config()


def _serialize(s: NextStepSuggestion, titles: dict[int, str]) -> dict:
    return {
        "id": s.id,
        "research_question_id": s.research_question_id,
        "suggested_direction": s.suggested_direction,
        "recommended_conversation_id": s.recommended_conversation_id,
        "recommended_conversation_title": titles.get(s.recommended_conversation_id)
        if s.recommended_conversation_id
        else None,
        "rationale": s.rationale,
        "status": s.status,
        "ai_metadata": json.loads(s.ai_metadata) if s.ai_metadata else None,
        "created_at": s.created_at.isoformat(),
    }


def _titles_for(cortico_db: Session, suggestions: list[NextStepSuggestion]) -> dict[int, str]:
    conv_ids = {s.recommended_conversation_id for s in suggestions if s.recommended_conversation_id}
    if not conv_ids:
        return {}
    return {c.id: c.title for c in cortico_db.query(Conversation).filter(Conversation.id.in_(conv_ids))}


@router.post("/generate")
def generate(
    cortico_db: Session = Depends(get_cortico_db), prototype_db: Session = Depends(get_prototype_db)
):
    created = generate_next_step_suggestions(
        prototype_db=prototype_db, cortico_db=cortico_db, config=config, user_id=config.default_user_id
    )
    titles = _titles_for(cortico_db, created)
    return [_serialize(s, titles) for s in created]


@router.get("")
def list_suggestions(
    include_dismissed: bool = False,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    query = prototype_db.query(NextStepSuggestion).filter(NextStepSuggestion.user_id == config.default_user_id)
    if not include_dismissed:
        query = query.filter(NextStepSuggestion.status != "dismissed")
    suggestions = query.order_by(NextStepSuggestion.created_at.desc()).all()
    titles = _titles_for(cortico_db, suggestions)
    return [_serialize(s, titles) for s in suggestions]


@router.post("/{suggestion_id}/accept")
def accept(suggestion_id: int, prototype_db: Session = Depends(get_prototype_db)):
    s = prototype_db.get(NextStepSuggestion, suggestion_id)
    if s is None:
        raise HTTPException(404, "suggestion not found")
    s.status = "accepted"
    prototype_db.commit()
    return {"id": s.id, "status": s.status}


@router.post("/{suggestion_id}/dismiss")
def dismiss(suggestion_id: int, prototype_db: Session = Depends(get_prototype_db)):
    s = prototype_db.get(NextStepSuggestion, suggestion_id)
    if s is None:
        raise HTTPException(404, "suggestion not found")
    s.status = "dismissed"
    prototype_db.commit()
    return {"id": s.id, "status": s.status}
