"""Prototype-owned tables, V2-shaped where Cortico has an equivalent object.

Table/column choices follow docs/prototype-log.md where they diverge from the PRD's
data-model section (notably: `highlight` -> `rl_highlight` to avoid colliding with
Cortico's own read-only `highlight` table, and `snippet_uuid` -> `snippet_id` since
snippets here carry no UUID).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import PrototypeBase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchQuestion(PrototypeBase):
    __tablename__ = "research_question"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=_now)


class RLHighlight(PrototypeBase):
    """Mirrors Cortico's `Highlight`/`CreateHighlightSchema` shape; renamed from the PRD's
    `highlight` to avoid colliding with Cortico's own read-only `highlight` table."""

    __tablename__ = "rl_highlight"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    conversation_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    title = Column(String)
    notes = Column(Text)  # the margin memo
    starred = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    snippets = relationship("HighlightSnippet", backref="highlight", cascade="all, delete-orphan")


class HighlightSnippet(PrototypeBase):
    __tablename__ = "highlight_snippet"
    id = Column(Integer, primary_key=True)
    highlight_id = Column(Integer, ForeignKey("rl_highlight.id"), nullable=False)
    snippet_id = Column(Integer, nullable=False)  # Cortico snippet.id (no uuid in schema.sql)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)


class VoiceMemo(PrototypeBase):
    __tablename__ = "voice_memo"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    conversation_id = Column(Integer, nullable=False)
    audio_path = Column(String, nullable=False)
    duration = Column(Float)
    recorded_at = Column(DateTime, nullable=False, default=_now)
    transcription_raw = Column(Text)  # JSON: [{word,start,end,confidence}, ...]
    transcription_edited = Column(Text)
    transcription_engine = Column(String)
    transcription_progress = Column(Float, nullable=False, default=0.0)  # 0..1, while transcribing
    transcription_error = Column(Text)
    extracted_interests = Column(Text)  # JSON: list[str]
    status = Column(String, nullable=False, default="recorded")
    # recorded -> transcribing -> ready_for_review | failed


class ReflectionConnection(PrototypeBase):
    __tablename__ = "reflection_connection"
    id = Column(Integer, primary_key=True)
    voice_memo_id = Column(Integer, ForeignKey("voice_memo.id"), nullable=False)
    research_question_id = Column(Integer, ForeignKey("research_question.id"), nullable=True)
    insight_text = Column(Text, nullable=False)
    source = Column(String, nullable=False)  # user | ai
    status = Column(String, nullable=False, default="suggested")
    # suggested -> accepted | edited | rejected ; accepted/edited can later -> retracted
    edited_from_ai = Column(Boolean, nullable=False, default=False)
    ai_metadata = Column(Text)  # JSON: {model, reasoning_effort, prompt, confidence, rationale}
    memo_order = Column(Integer)  # manual reorder within its RQ section; falls back to created_at
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    evidence = relationship("ConnectionEvidence", backref="connection", cascade="all, delete-orphan")
    revisions = relationship(
        "ReflectionConnectionRevision", backref="connection", cascade="all, delete-orphan"
    )


class ConnectionEvidence(PrototypeBase):
    __tablename__ = "connection_evidence"
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("reflection_connection.id"), nullable=False)
    highlight_id = Column(Integer, ForeignKey("rl_highlight.id"), nullable=True)
    snippet_id = Column(Integer, nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    source = Column(String, nullable=False)  # user | ai
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)


class ReflectionConnectionRevision(PrototypeBase):
    __tablename__ = "reflection_connection_revision"
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("reflection_connection.id"), nullable=False)
    insight_text = Column(Text, nullable=False)
    evidence_snapshot = Column(Text, nullable=False)  # JSON snapshot of evidence rows
    changed_at = Column(DateTime, nullable=False, default=_now)


class TranscriptState(PrototypeBase):
    __tablename__ = "transcript_state"
    user_id = Column(Integer, nullable=False)
    conversation_id = Column(Integer, nullable=False)
    reached_end_at = Column(DateTime)
    prompt_dismissed_at = Column(DateTime)

    __table_args__ = (PrimaryKeyConstraint("user_id", "conversation_id"),)


class SectionCheckpoint(PrototypeBase):
    __tablename__ = "section_checkpoint"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    conversation_id = Column(Integer, nullable=False)
    snippet_id = Column(Integer, nullable=False)
    guide_question_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "conversation_id", "guide_question_id", name="uq_checkpoint_per_question"
        ),
    )


class AppSetting(PrototypeBase):
    """Not in the PRD's data model — added to persist the editable AI-review prompt
    (view/save/reset-to-default) across restarts. See docs/prototype-log.md."""

    __tablename__ = "app_setting"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)
