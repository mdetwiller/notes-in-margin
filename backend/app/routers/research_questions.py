from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_prototype_db
from ..models_prototype import ResearchQuestion
from ..schemas import ReorderRequest, ResearchQuestionCreate, ResearchQuestionUpdate

router = APIRouter(prefix="/research_questions", tags=["research_questions"])
config = get_config()


def _serialize(rq: ResearchQuestion) -> dict:
    return {
        "id": rq.id,
        "name": rq.name,
        "description": rq.description,
        "display_order": rq.display_order,
        "archived": rq.archived,
    }


@router.get("")
def list_research_questions(
    include_archived: bool = False, prototype_db: Session = Depends(get_prototype_db)
):
    query = prototype_db.query(ResearchQuestion).filter(
        ResearchQuestion.user_id == config.default_user_id
    )
    if not include_archived:
        query = query.filter(ResearchQuestion.archived.is_(False))
    rqs = query.order_by(ResearchQuestion.display_order).all()
    return [_serialize(rq) for rq in rqs]


@router.post("")
def create_research_question(
    body: ResearchQuestionCreate, prototype_db: Session = Depends(get_prototype_db)
):
    max_order = (
        prototype_db.query(ResearchQuestion)
        .filter(ResearchQuestion.user_id == config.default_user_id)
        .count()
    )
    rq = ResearchQuestion(
        user_id=config.default_user_id,
        project_id=config.default_project_id,
        name=body.name,
        description=body.description,
        display_order=max_order,
    )
    prototype_db.add(rq)
    prototype_db.commit()
    prototype_db.refresh(rq)
    return _serialize(rq)


@router.patch("/{rq_id}")
def update_research_question(
    rq_id: int, body: ResearchQuestionUpdate, prototype_db: Session = Depends(get_prototype_db)
):
    rq = prototype_db.get(ResearchQuestion, rq_id)
    if rq is None:
        raise HTTPException(404, "research question not found")
    if body.name is not None:
        rq.name = body.name
    if body.description is not None:
        rq.description = body.description
    if body.archived is not None:
        rq.archived = body.archived
    prototype_db.commit()
    prototype_db.refresh(rq)
    return _serialize(rq)


@router.put("/reorder")
def reorder_research_questions(
    body: ReorderRequest, prototype_db: Session = Depends(get_prototype_db)
):
    for order, rq_id in enumerate(body.ordered_ids):
        rq = prototype_db.get(ResearchQuestion, rq_id)
        if rq is not None:
            rq.display_order = order
    prototype_db.commit()
    return {"reordered": True}
