"""Structural validation + apply-results logic for code-family synthesis, mirroring
test_next_steps.py: pure/DB-level helpers are unit-tested directly against real data; the
live gpt-5.6-luna round trip is exercised manually (see docs/prototype-log.md) rather than
in automated tests."""
from fastapi.testclient import TestClient

from app.db import PrototypeSession
from app.main import app
from app.models_prototype import CodeFamily, CodeFamilyMember, ReflectionConnection, ResearchQuestion, VoiceMemo
from app.services.code_families import _apply_family_results, _valid_connection_ids

client = TestClient(app)

_DEFAULT_AI_METADATA = {"model": "m", "reasoning_effort": "low", "prompt": "p"}


def _make_rq(db, user_id=80001):
    rq = ResearchQuestion(user_id=user_id, project_id=5, name="test rq", display_order=0)
    db.add(rq)
    db.commit()
    db.refresh(rq)
    return rq


def _make_connection(db, rq_id, status="accepted", insight="an insight"):
    vm = VoiceMemo(user_id=80001, conversation_id=9, audio_path="x", status="filed")
    db.add(vm)
    db.commit()
    db.refresh(vm)
    c = ReflectionConnection(
        voice_memo_id=vm.id,
        research_question_id=rq_id,
        insight_text=insight,
        source="user",
        status=status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_valid_connection_ids_only_includes_accepted_or_edited_in_this_rq():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        other_rq = _make_rq(db)
        accepted = _make_connection(db, rq.id, status="accepted")
        edited = _make_connection(db, rq.id, status="edited")
        suggested = _make_connection(db, rq.id, status="suggested")
        wrong_rq = _make_connection(db, other_rq.id, status="accepted")

        valid = _valid_connection_ids(db, rq.id)
        assert valid == {accepted.id, edited.id}
        assert suggested.id not in valid
        assert wrong_rq.id not in valid
    finally:
        db.close()


def test_apply_family_results_creates_new_family_with_valid_members_only():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        c1 = _make_connection(db, rq.id)
        c2 = _make_connection(db, rq.id)
        valid_ids = {c1.id, c2.id}

        raw = [
            {
                "existing_family_id": None,
                "name": "Trust in institutions",
                "definition": "Entries about trusting or distrusting local institutions.",
                "member_connection_ids": [c1.id, c2.id, 999_999],  # last one invalid, must be dropped
            }
        ]
        touched = _apply_family_results(
            db,
            research_question_id=rq.id,
            user_id=80001,
            raw_families=raw,
            valid_connection_ids=valid_ids,
            existing_family_ids=set(),
            ai_metadata=_DEFAULT_AI_METADATA,
        )
        assert len(touched) == 1
        family = touched[0]
        assert family.name == "Trust in institutions"
        assert {m.connection_id for m in family.members} == {c1.id, c2.id}
    finally:
        db.close()


def test_apply_family_results_attaches_to_existing_family_instead_of_duplicating():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        c1 = _make_connection(db, rq.id)
        c2 = _make_connection(db, rq.id)

        existing = CodeFamily(
            user_id=80001, research_question_id=rq.id, name="Existing family", definition="d", status="accepted"
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        db.add(CodeFamilyMember(code_family_id=existing.id, connection_id=c1.id))
        db.commit()

        raw = [
            {
                "existing_family_id": existing.id,
                "name": None,
                "definition": None,
                "member_connection_ids": [c1.id, c2.id],  # c1 already a member, c2 new
            }
        ]
        touched = _apply_family_results(
            db,
            research_question_id=rq.id,
            user_id=80001,
            raw_families=raw,
            valid_connection_ids={c1.id, c2.id},
            existing_family_ids={existing.id},
            ai_metadata=_DEFAULT_AI_METADATA,
        )
        assert len(touched) == 1
        assert touched[0].id == existing.id

        all_families = db.query(CodeFamily).filter(CodeFamily.research_question_id == rq.id).all()
        assert len(all_families) == 1  # no duplicate created
        assert {m.connection_id for m in existing.members} == {c1.id, c2.id}
    finally:
        db.close()


def test_apply_family_results_drops_family_with_no_valid_members():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        raw = [
            {
                "existing_family_id": None,
                "name": "Hallucinated family",
                "definition": "d",
                "member_connection_ids": [999_999],
            }
        ]
        touched = _apply_family_results(
            db,
            research_question_id=rq.id,
            user_id=80001,
            raw_families=raw,
            valid_connection_ids=set(),
            existing_family_ids=set(),
            ai_metadata=_DEFAULT_AI_METADATA,
        )
        assert touched == []
        assert db.query(CodeFamily).filter(CodeFamily.research_question_id == rq.id).count() == 0
    finally:
        db.close()


def test_apply_family_results_falls_back_to_new_family_when_existing_id_invalid():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        c1 = _make_connection(db, rq.id)

        raw = [
            {
                "existing_family_id": 999_999,  # not in existing_family_ids
                "name": "Fallback family",
                "definition": "d",
                "member_connection_ids": [c1.id],
            }
        ]
        touched = _apply_family_results(
            db,
            research_question_id=rq.id,
            user_id=80001,
            raw_families=raw,
            valid_connection_ids={c1.id},
            existing_family_ids=set(),
            ai_metadata=_DEFAULT_AI_METADATA,
        )
        assert len(touched) == 1
        assert touched[0].name == "Fallback family"
    finally:
        db.close()


def test_rename_redefine_accept_persist_and_reload():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        c1 = _make_connection(db, rq.id)
        family = CodeFamily(
            user_id=80001, research_question_id=rq.id, name="Orig", definition="orig def", status="suggested"
        )
        db.add(family)
        db.commit()
        db.refresh(family)
        db.add(CodeFamilyMember(code_family_id=family.id, connection_id=c1.id))
        db.commit()
        family_id = family.id
        rq_id = rq.id
        c1_id = c1.id
    finally:
        db.close()

    renamed = client.patch(f"/code_families/{family_id}", json={"name": "Renamed", "definition": "new def"}).json()
    assert renamed["name"] == "Renamed"
    assert renamed["definition"] == "new def"
    assert len(renamed["members"]) == 1
    assert renamed["members"][0]["connection_id"] == c1_id

    accepted = client.post(f"/code_families/{family_id}/accept").json()
    assert accepted["status"] == "accepted"

    default_list = client.get(f"/research_questions/{rq_id}/code_families").json()
    assert any(f["id"] == family_id and f["name"] == "Renamed" and f["status"] == "accepted" for f in default_list)


def test_dismissed_family_hidden_by_default_but_not_deleted():
    db = PrototypeSession()
    try:
        rq = _make_rq(db)
        family = CodeFamily(
            user_id=80001, research_question_id=rq.id, name="To dismiss", definition="d", status="suggested"
        )
        db.add(family)
        db.commit()
        db.refresh(family)
        family_id = family.id
        rq_id = rq.id
    finally:
        db.close()

    client.post(f"/code_families/{family_id}/dismiss")

    default_list = client.get(f"/research_questions/{rq_id}/code_families").json()
    assert all(f["id"] != family_id for f in default_list)

    with_dismissed = client.get(f"/research_questions/{rq_id}/code_families?include_dismissed=true").json()
    assert any(f["id"] == family_id for f in with_dismissed)


def test_synthesize_on_unknown_research_question_404s():
    resp = client.post("/research_questions/999999/code_families/synthesize")
    assert resp.status_code == 404
