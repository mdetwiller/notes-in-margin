from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..models_prototype import CodeFamily, ReflectionConnection, ResearchQuestion
from ..schemas import CodeFamilyUpdate
from ..services.code_families import synthesize_code_families

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


def _list_for_rq(prototype_db: Session, rq_id: int, include_dismissed: bool) -> list[dict]:
    query = prototype_db.query(CodeFamily).filter(CodeFamily.research_question_id == rq_id)
    if not include_dismissed:
        query = query.filter(CodeFamily.status != "dismissed")
    families = query.order_by(CodeFamily.created_at).all()
    insight_by_connection = _insight_texts_for(prototype_db, families)
    return [_serialize(f, insight_by_connection) for f in families]


@router.get("/research_questions/{rq_id}/code_families")
def list_code_families(
    rq_id: int, include_dismissed: bool = False, prototype_db: Session = Depends(get_prototype_db)
):
    return _list_for_rq(prototype_db, rq_id, include_dismissed)


@router.post("/research_questions/{rq_id}/code_families/synthesize")
def synthesize(
    rq_id: int,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    rq = prototype_db.get(ResearchQuestion, rq_id)
    if rq is None:
        raise HTTPException(404, "research question not found")
    synthesize_code_families(
        prototype_db=prototype_db,
        cortico_db=cortico_db,
        config=config,
        user_id=config.default_user_id,
        research_question_id=rq_id,
    )
    return _list_for_rq(prototype_db, rq_id, include_dismissed=False)


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
