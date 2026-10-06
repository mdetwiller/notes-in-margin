"""The file-to-memo transaction is the single write point for the memo: nothing should
reach status accepted/edited before POST /voice_memos/{id}/file is called."""
from fastapi.testclient import TestClient

from app.db import PrototypeSession
from app.main import app
from app.models_prototype import ReflectionConnection, VoiceMemo

client = TestClient(app)


def _make_voice_memo(conversation_id: int = 9) -> int:
    db = PrototypeSession()
    try:
        vm = VoiceMemo(
            user_id=101,
            conversation_id=conversation_id,
            audio_path="db/local/audio/test.webm",
            duration=5.0,
            transcription_edited="test reflection",
            status="ready_for_review",
        )
        db.add(vm)
        db.commit()
        db.refresh(vm)
        return vm.id
    finally:
        db.close()


def test_user_added_connection_is_untouched_until_filed():
    rq = client.post("/research_questions", json={"name": "test rq for filing"}).json()
    vm_id = _make_voice_memo()

    # Before filing: no connection exists at all for this voice memo yet.
    review = client.get(f"/voice_memos/{vm_id}/review").json()
    assert review["connections"] == []

    body = {
        "decisions": [
            {
                "connection_id": None,
                "action": "accept",
                "research_question_id": rq["id"],
                "insight_text": "a connection the AI missed, added by the user",
                "evidence": [],
            }
        ]
    }
    filed = client.post(f"/voice_memos/{vm_id}/file", json=body).json()
    assert len(filed["connections"]) == 1
    assert filed["connections"][0]["status"] == "accepted"
    assert filed["connections"][0]["source"] == "user"

    vm_after = client.get(f"/voice_memos/{vm_id}").json()
    assert vm_after["status"] == "filed"

    # It now shows up in the memo, under the right RQ.
    memo = client.get("/memo").json()
    section = next(s for s in memo["sections"] if s["research_question_id"] == rq["id"])
    assert len(section["entries"]) == 1
    assert section["entries"][0]["insight_text"] == "a connection the AI missed, added by the user"


def test_rejecting_a_suggested_connection_keeps_it_logged_not_deleted():
    db = PrototypeSession()
    try:
        vm_id = _make_voice_memo()
        connection = ReflectionConnection(
            voice_memo_id=vm_id,
            research_question_id=None,
            insight_text="an AI proposal the user will reject",
            source="ai",
            status="suggested",
        )
        db.add(connection)
        db.commit()
        connection_id = connection.id
    finally:
        db.close()

    body = {"decisions": [{"connection_id": connection_id, "action": "reject"}]}
    filed = client.post(f"/voice_memos/{vm_id}/file", json=body).json()
    rejected = next(c for c in filed["connections"] if c["id"] == connection_id)
    assert rejected["status"] == "rejected"  # kept in the log, not removed


def test_checkpoint_move_replaces_rather_than_duplicates():
    client.put("/conversations/9/checkpoints", json={"guide_question_id": 4, "snippet_id": 1936})
    client.put("/conversations/9/checkpoints", json={"guide_question_id": 4, "snippet_id": 1938})

    detail = client.get("/conversations/9").json()
    q4 = next(q for q in detail["guide_questions"] if q["guide_question_id"] == 4)
    assert q4["checkpoint_snippet_id"] == 1938  # moved, not duplicated
