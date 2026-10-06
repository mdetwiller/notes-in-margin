"""Conversation-guide resolution.

PRD open question, resolved: V2 guides belong to a project and (per the PRD's assumption)
conversations may carry no guide ID, so fall back to the project's latest guide version.
In this snapshot `conversation.conversation_guide_id` exists as a column but is NULL for
every conversation (see docs/prototype-log.md), so the fallback path below is what actually
runs for all of this prototype's test data.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models_cortico import Conversation, ConversationGuide, GuideQuestion, GuideSection


def resolve_guide(cortico_db: Session, conversation: Conversation) -> ConversationGuide | None:
    if conversation.conversation_guide_id:
        guide = (
            cortico_db.query(ConversationGuide)
            .filter(ConversationGuide.id == conversation.conversation_guide_id)
            .one_or_none()
        )
        if guide:
            return guide

    # No published/status flag on conversationguide in this schema, so "latest" = max version.
    return (
        cortico_db.query(ConversationGuide)
        .filter(ConversationGuide.project_id == conversation.project_id)
        .order_by(ConversationGuide.version.desc())
        .first()
    )


def guide_questions_in_order(
    cortico_db: Session, guide: ConversationGuide
) -> list[GuideQuestion]:
    sections = (
        cortico_db.query(GuideSection)
        .filter(GuideSection.conversation_guide_id == guide.id)
        .order_by(GuideSection.order_index)
        .all()
    )
    questions: list[GuideQuestion] = []
    for section in sections:
        questions.extend(
            cortico_db.query(GuideQuestion)
            .filter(GuideQuestion.guide_section_id == section.id)
            .order_by(GuideQuestion.order_index)
            .all()
        )
    return questions
