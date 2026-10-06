from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_prototype_db
from ..schemas import PromptUpdate
from ..services import ai_review

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/review-prompt")
def get_review_prompt(prototype_db: Session = Depends(get_prototype_db)):
    return {
        "text": ai_review.get_review_prompt(prototype_db),
        "default_text": ai_review.DEFAULT_REVIEW_PROMPT,
    }


@router.put("/review-prompt")
def save_review_prompt(body: PromptUpdate, prototype_db: Session = Depends(get_prototype_db)):
    ai_review.set_review_prompt(prototype_db, body.text)
    return {"text": body.text}


@router.post("/review-prompt/reset")
def reset_review_prompt(prototype_db: Session = Depends(get_prototype_db)):
    text = ai_review.reset_review_prompt(prototype_db)
    return {"text": text}
