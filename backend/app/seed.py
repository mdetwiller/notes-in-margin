from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from .config import BACKEND_DIR, get_config
from .models_prototype import ResearchQuestion

SEED_PATH = BACKEND_DIR / "seed" / "research_questions.seed.json"


def seed_research_questions(prototype_db: Session) -> None:
    """Loads RQs from the config-file seed on first run only (PRD: "Lists the user's RQs,
    seeded from a config file at startup"). No-ops if the user already has any RQs."""
    config = get_config()
    existing = (
        prototype_db.query(ResearchQuestion)
        .filter(ResearchQuestion.user_id == config.default_user_id)
        .count()
    )
    if existing:
        return

    seed_rqs: list[dict] = json.loads(Path(SEED_PATH).read_text())
    for rq in seed_rqs:
        prototype_db.add(
            ResearchQuestion(
                user_id=config.default_user_id,
                project_id=config.default_project_id,
                name=rq["name"],
                description=rq.get("description"),
                display_order=rq.get("display_order", 0),
            )
        )
    prototype_db.commit()
