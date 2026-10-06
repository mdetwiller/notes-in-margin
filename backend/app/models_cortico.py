"""Read-only mappings onto the Cortico tables in acp_pipeline_snapshot.db.

Field names/types follow db/schema.sql (the real snapshot), not the PRD's V2 OpenAPI
summary, per the PRD's own instruction. See docs/prototype-log.md for every delta.

Nothing in this file is ever add()-ed or commit()-ed; the engine itself (app/db.py) is
opened read-only, so there is no write path through these models regardless.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, Integer, String

from .db import CorticoBase


class Organization(CorticoBase):
    __tablename__ = "organization"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    name = Column(String, nullable=False)


class Community(CorticoBase):
    __tablename__ = "community"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    organization_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)


class Forum(CorticoBase):
    __tablename__ = "forum"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    community_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    is_public = Column(Boolean, nullable=False)


class Project(CorticoBase):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    organization_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)


class Participant(CorticoBase):
    __tablename__ = "participant"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    is_facilitator = Column(Boolean, nullable=False)
    is_registered_user = Column(Boolean, nullable=False)
    cortico_user_id = Column(Integer)


class Conversation(CorticoBase):
    __tablename__ = "conversation"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    forum_id = Column(Integer)
    project_id = Column(Integer)
    conversation_guide_id = Column(Integer)
    title = Column(String, nullable=False)
    audio_url = Column(String)
    duration_seconds = Column(Float)
    language = Column(String)
    is_open = Column(Boolean, nullable=False)
    facilitator_participant_id = Column(Integer)


class Snippet(CorticoBase):
    __tablename__ = "snippet"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    conversation_id = Column(Integer, nullable=False)
    participant_id = Column(Integer)
    order_index = Column(Integer, nullable=False)
    start_offset = Column(Float, nullable=False)
    end_offset = Column(Float, nullable=False)
    text = Column(String, nullable=False)
    words = Column(String)  # JSON array of {word, start, end, confidence}
    is_facilitator_prompt = Column(Boolean, nullable=False)
    is_mechanical = Column(Boolean, nullable=False)
    ai_score = Column(Float)


class ConversationGuide(CorticoBase):
    __tablename__ = "conversationguide"
    id = Column(Integer, primary_key=True)
    cortico_id = Column(Integer)
    project_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    version = Column(Integer, nullable=False)


class GuideSection(CorticoBase):
    __tablename__ = "guidesection"
    id = Column(Integer, primary_key=True)
    conversation_guide_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)


class GuideQuestion(CorticoBase):
    __tablename__ = "guidequestion"
    id = Column(Integer, primary_key=True)
    guide_section_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    shorthand_code = Column(String)
    order_index = Column(Integer, nullable=False)
