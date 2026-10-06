from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_config
from ..db import get_cortico_db, get_prototype_db
from ..models_cortico import Conversation
from ..models_prototype import HighlightSnippet, RLHighlight
from ..schemas import HighlightCreate, HighlightUpdate

router = APIRouter(tags=["highlights"])
config = get_config()


def _serialize(h: RLHighlight) -> dict:
    return {
        "id": h.id,
        "conversation_id": h.conversation_id,
        "title": h.title,
        "notes": h.notes,
        "starred": h.starred,
        "created_at": h.created_at.isoformat(),
        "snippets": [
            {"snippet_id": s.snippet_id, "start_index": s.start_index, "end_index": s.end_index}
            for s in h.snippets
        ],
    }


@router.get("/conversations/{conversation_id}/highlights")
def list_highlights(conversation_id: int, prototype_db: Session = Depends(get_prototype_db)):
    highlights = (
        prototype_db.query(RLHighlight)
        .filter(
            RLHighlight.user_id == config.default_user_id,
            RLHighlight.conversation_id == conversation_id,
        )
        .order_by(RLHighlight.created_at)
        .all()
    )
    return [_serialize(h) for h in highlights]


@router.post("/conversations/{conversation_id}/highlights")
def create_highlight(
    conversation_id: int,
    body: HighlightCreate,
    cortico_db: Session = Depends(get_cortico_db),
    prototype_db: Session = Depends(get_prototype_db),
):
    conversation = cortico_db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "conversation not found")

    highlight = RLHighlight(
        user_id=config.default_user_id,
        conversation_id=conversation_id,
        project_id=conversation.project_id,
        title=body.title,
        notes=body.notes,
    )
    prototype_db.add(highlight)
    prototype_db.flush()
    for snip in body.snippets:
        prototype_db.add(
            HighlightSnippet(
                highlight_id=highlight.id,
                snippet_id=snip.snippet_id,
                start_index=snip.start_index,
                end_index=snip.end_index,
            )
        )
    prototype_db.commit()
    prototype_db.refresh(highlight)
    return _serialize(highlight)


@router.patch("/highlights/{highlight_id}")
def update_highlight(
    highlight_id: int, body: HighlightUpdate, prototype_db: Session = Depends(get_prototype_db)
):
    highlight = prototype_db.get(RLHighlight, highlight_id)
    if highlight is None:
        raise HTTPException(404, "highlight not found")
    if body.title is not None:
        highlight.title = body.title
    if body.notes is not None:
        highlight.notes = body.notes
    if body.starred is not None:
        highlight.starred = body.starred
    prototype_db.commit()
    prototype_db.refresh(highlight)
    return _serialize(highlight)


@router.delete("/highlights/{highlight_id}")
def delete_highlight(highlight_id: int, prototype_db: Session = Depends(get_prototype_db)):
    highlight = prototype_db.get(RLHighlight, highlight_id)
    if highlight is None:
        raise HTTPException(404, "highlight not found")
    prototype_db.delete(highlight)
    prototype_db.commit()
    return {"deleted": True}
