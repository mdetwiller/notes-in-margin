"""Regression coverage for the Phase 2 scope-widening + project_id bug fix:
create_highlight used to hardcode project_id=config.default_project_id (always 5),
mislabeling every highlight made outside project 5."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_conversations_is_not_scoped_to_project_5():
    conversations = client.get("/conversations").json()
    assert len(conversations) == 201
    project_ids = {c["project_id"] for c in conversations}
    assert project_ids != {5}


def test_highlight_outside_project_5_gets_real_project_id():
    # Conversation 1 belongs to project 1, not the default project (5).
    body = {"title": "test highlight", "notes": "", "snippets": []}
    created = client.post("/conversations/1/highlights", json=body).json()
    assert created["conversation_id"] == 1

    conversation = client.get("/conversations/1").json()
    assert conversation["id"] == 1

    # project_id isn't in the highlight's own serialized payload, so check the row directly.
    from app.db import PrototypeSession
    from app.models_prototype import RLHighlight

    db = PrototypeSession()
    try:
        row = db.get(RLHighlight, created["id"])
        assert row.project_id == 1
    finally:
        db.close()


def test_create_highlight_on_unknown_conversation_404s():
    body = {"title": None, "notes": None, "snippets": []}
    resp = client.post("/conversations/999999/highlights", json=body)
    assert resp.status_code == 404
