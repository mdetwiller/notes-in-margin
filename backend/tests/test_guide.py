"""Guide resolution against the real snapshot: every conversation.conversation_guide_id is
NULL in this data, so these tests exercise the actual fallback path, not a mocked one."""
from app.db import CorticoSession
from app.guide import guide_questions_in_order, resolve_guide
from app.models_cortico import Conversation


def test_resolve_guide_falls_back_to_latest_project_version():
    db = CorticoSession()
    try:
        conversation = db.get(Conversation, 9)
        assert conversation.conversation_guide_id is None  # confirms the fallback path runs

        guide = resolve_guide(db, conversation)
        assert guide is not None
        assert guide.project_id == conversation.project_id
    finally:
        db.close()


def test_resolve_guide_returns_none_for_project_without_a_guide():
    db = CorticoSession()
    try:
        # Project 1 (Yankton) has conversations but no conversationguide row at all.
        fake = Conversation(id=0, project_id=1, title="x", is_open=True, conversation_guide_id=None)
        guide = resolve_guide(db, fake)
        assert guide is None
    finally:
        db.close()


def test_guide_questions_come_back_in_transcript_order():
    """order_index resets to 0 at the start of each guidesection, so overall order comes
    from (section order, then question order within it) — not a single monotonic column."""
    db = CorticoSession()
    try:
        conversation = db.get(Conversation, 9)
        guide = resolve_guide(db, conversation)
        questions = guide_questions_in_order(db, guide)
        codes = [q.shorthand_code for q in questions]
        assert codes[0] == "Consent"
        assert codes[1] == "Guidelines"
        assert codes[2] == "Q1 Intros"
        assert len(questions) >= 6  # PRD: "typically 5-6" guide questions
    finally:
        db.close()
