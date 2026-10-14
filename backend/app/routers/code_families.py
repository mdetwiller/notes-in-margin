from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..models_prototype import CodeFamily, CodeFamilyMergeSuggestion, ReflectionConnection, ResearchQuestion
from ..schemas import CodeFamilyUpdate
from ..services.code_families import (
    LIVE_FAMILY_STATUSES,
    accept_merge,
    cap_status,
    synthesize_code_families,
)

router = APIRouter(tags=["code_families"])
config = get_config()


def _insight_texts_for(prototype_db: Session, families: list[CodeFamily]) -> dict[int, str]:
    connection_ids = {m.connection_id for f in families for m in f.members}
    if not connection_ids:
        return {}
    return {
        c.id: c.insight_text
        for c in prototype_db.query(ReflectionConnection).filter(ReflectionConnection.id.in_(connection_ids))
    }


def _serialize(family: CodeFamily, insight_by_connection: dict[int, str]) -> dict:
    return {
        "id": family.id,
        "research_question_id": family.research_question_id,
        "name": family.name,
        "definition": family.definition,
        "status": family.status,
        "ai_metadata": json.loads(family.ai_metadata) if family.ai_metadata else None,
        "created_at": family.created_at.isoformat(),
        "members": [
            {"connection_id": m.connection_id, "insight_text": insight_by_connection.get(m.connection_id, "")}
            for m in family.members
        ],
    }


def _serialize_merge(m: CodeFamilyMergeSuggestion) -> dict:
    return {
        "id": m.id,
        "research_question_id": m.research_question_id,
        "family_ids": json.loads(m.family_ids_json),
        "target_family_id": m.target_family_id,
        "proposed_name": m.proposed_name,
        "proposed_definition": m.proposed_definition,
        "rationale": m.rationale,
        "status": m.status,
        "ai_metadata": json.loads(m.ai_metadata) if m.ai_metadata else None,
        "created_at": m.created_at.isoformat(),
    }


def _pending_merges(prototype_db: Session, rq_id: int) -> list[dict]:
    """Pending merge suggestions whose families are all still live — one whose family was
    dismissed or merged elsewhere since is stale and just hidden (still logged)."""
    live_ids = {
        f.id
        for f in prototype_db.query(CodeFamily.id).filter(
            CodeFamily.research_question_id == rq_id, CodeFamily.status.in_(LIVE_FAMILY_STATUSES)
        )
    }
    merges = (
        prototype_db.query(CodeFamilyMergeSuggestion)
        .filter(CodeFamilyMergeSuggestion.research_question_id == rq_id, CodeFamilyMergeSuggestion.status == "suggested")
        .order_by(CodeFamilyMergeSuggestion.created_at)
        .all()
    )
    return [_serialize_merge(m) for m in merges if set(json.loads(m.family_ids_json)) <= live_ids]


def _state_for_rq(prototype_db: Session, rq_id: int, withheld_new_families: int = 0) -> dict:
    families = _list_for_rq(prototype_db, rq_id, include_dismissed=False)
    live_count = sum(1 for f in families if f["status"] in LIVE_FAMILY_STATUSES)
    cap = cap_status(live_count, config.code_families, override_cap=False)
    return {
        "families": families,
        "merge_suggestions": _pending_merges(prototype_db, rq_id),
        "cap": {
            "live_count": cap.live_count,
            "max_per_rq": cap.max_per_rq,
            "near_cap": cap.near_cap,
            "at_cap": cap.live_count >= cap.max_per_rq,
        },
        "withheld_new_families": withheld_new_families,
    }


def _list_for_rq(prototype_db: Session, rq_id: int, include_dismissed: bool) -> list[dict]:
    query = prototype_db.query(CodeFamily).filter(CodeFamily.research_question_id == rq_id)
    if not include_dismissed:
        query = query.filter(CodeFamily.status.in_(LIVE_FAMILY_STATUSES))
    families = query.order_by(CodeFamily.created_at).all()
    insight_by_connection = _insight_texts_for(prototype_db, families)
    return [_serialize(f, insight_by_connection) for f in families]


@router.get("/research_questions/{rq_id}/code_families")
def list_code_families(
    rq_id: int, include_dismissed: bool = False, prototype_db: Session = Depends(get_prototype_db)
):
    return _list_for_rq(prototype_db, rq_id, include_dismissed)


@router.get("/research_questions/{rq_id}/code_families/state")
def code_family_state(rq_id: int, prototype_db: Session = Depends(get_prototype_db)):
    """Families plus pending merge suggestions and where the RQ stands against its cap."""
    return _state_for_rq(prototype_db, rq_id)


@router.post("/research_questions/{rq_id}/code_families/synthesize")
def synthesize(
    rq_id: int,
    override_cap: bool = False,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    rq = prototype_db.get(ResearchQuestion, rq_id)
    if rq is None:
        raise HTTPException(404, "research question not found")
    result = synthesize_code_families(
        prototype_db=prototype_db,
        cortico_db=cortico_db,
        config=config,
        user_id=config.default_user_id,
        research_question_id=rq_id,
        override_cap=override_cap,
    )
    return _state_for_rq(prototype_db, rq_id, withheld_new_families=result.withheld_new_families)


@router.patch("/code_families/{family_id}")
def update_family(family_id: int, body: CodeFamilyUpdate, prototype_db: Session = Depends(get_prototype_db)):
    family = prototype_db.get(CodeFamily, family_id)
    if family is None:
        raise HTTPException(404, "code family not found")
    if body.name is not None:
        family.name = body.name
    if body.definition is not None:
        family.definition = body.definition
    prototype_db.commit()
    prototype_db.refresh(family)
    return _serialize(family, _insight_texts_for(prototype_db, [family]))


@router.post("/code_families/{family_id}/accept")
def accept_family(family_id: int, prototype_db: Session = Depends(get_prototype_db)):
    family = prototype_db.get(CodeFamily, family_id)
    if family is None:
        raise HTTPException(404, "code family not found")
    family.status = "accepted"
    prototype_db.commit()
    return {"id": family.id, "status": family.status}


@router.post("/code_families/{family_id}/dismiss")
def dismiss_family(family_id: int, prototype_db: Session = Depends(get_prototype_db)):
    family = prototype_db.get(CodeFamily, family_id)
    if family is None:
        raise HTTPException(404, "code family not found")
    family.status = "dismissed"
    prototype_db.commit()
    return {"id": family.id, "status": family.status}


@router.post("/code_family_merges/{merge_id}/accept")
def accept_merge_suggestion(merge_id: int, prototype_db: Session = Depends(get_prototype_db)):
    suggestion = prototype_db.get(CodeFamilyMergeSuggestion, merge_id)
    if suggestion is None:
        raise HTTPException(404, "merge suggestion not found")
    if suggestion.status != "suggested":
        raise HTTPException(409, f"merge suggestion is already {suggestion.status}")
    try:
        accept_merge(prototype_db, suggestion)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return _state_for_rq(prototype_db, suggestion.research_question_id)


@router.post("/code_family_merges/{merge_id}/dismiss")
def dismiss_merge_suggestion(merge_id: int, prototype_db: Session = Depends(get_prototype_db)):
    suggestion = prototype_db.get(CodeFamilyMergeSuggestion, merge_id)
    if suggestion is None:
        raise HTTPException(404, "merge suggestion not found")
    suggestion.status = "dismissed"
    prototype_db.commit()
    return {"id": suggestion.id, "status": suggestion.status}
