"""Evidence provenance: every evidence write links the passage to the user's highlight it
overlaps (connection_evidence.highlight_id), so `yours` badges, the starred flag, and
"starred, unassigned" all follow the real link rather than an exact-span guess.

Each test uses its own conversation so highlights created by other tests can't overlap.
"""
import json

from fastapi.testclient import TestClient

from app.config import get_config
from app.db import CorticoSession, PrototypeSession
from app.evidence_provenance import HighlightSpan, match_highlight
from app.main import app
from app.models_cortico import Snippet
from app.models_prototype import (
    ConnectionEvidence,
    HighlightSnippet,
    ReflectionConnection,
    ResearchQuestion,
    RLHighlight,
    VoiceMemo,
)
from app.services.ai_review import persist_review_result

client = TestClient(app)
config = get_config()
USER = config.default_user_id


def _long_snippets(conversation_id: int, n: int = 3, min_words: int = 20) -> list[int]:
    db = CorticoSession()
    try:
        snippets = (
            db.query(Snippet)
            .filter(Snippet.conversation_id == conversation_id)
            .order_by(Snippet.order_index)
            .all()
        )
        ids = [s.id for s in snippets if s.words and len(json.loads(s.words)) >= min_words][:n]
        assert len(ids) == n, f"conversation {conversation_id} lacks {n} long snippets"
        return ids
    finally:
        db.close()


def _highlight(db, conversation_id: int, snippet_id: int, start: int, end: int, starred: bool) -> int:
    h = RLHighlight(user_id=USER, conversation_id=conversation_id, project_id=5, notes="note", starred=starred)
    db.add(h)
    db.flush()
    db.add(HighlightSnippet(highlight_id=h.id, snippet_id=snippet_id, start_index=start, end_index=end))
    db.commit()
    return h.id


def _rq(db, name: str) -> int:
    rq = ResearchQuestion(user_id=USER, project_id=5, name=name)
    db.add(rq)
    db.commit()
    return rq.id


def _voice_memo(db, conversation_id: int) -> VoiceMemo:
    vm = VoiceMemo(
        user_id=USER,
        conversation_id=conversation_id,
        audio_path="db/local/audio/test.webm",
        transcription_edited="test reflection",
        status="ready_for_review",
    )
    db.add(vm)
    db.commit()
    return vm


# --- matching ------------------------------------------------------------------------


def test_match_is_by_overlap_and_prefers_starred_then_larger_overlap():
    spans = [
        HighlightSpan(1, False, 100, 0, 10),
        HighlightSpan(2, True, 100, 8, 12),
        HighlightSpan(3, False, 100, 20, 30),
        HighlightSpan(4, True, 200, 0, 10),
    ]
    assert match_highlight(spans, 100, 2, 6).highlight_id == 1  # partial overlap, not exact
    assert match_highlight(spans, 100, 5, 11).highlight_id == 2  # starred beats bigger overlap
    assert match_highlight(spans, 100, 22, 40).highlight_id == 3
    assert match_highlight(spans, 100, 10, 20) is not None  # 10..11 overlaps highlight 2
    assert match_highlight(spans, 100, 12, 20) is None  # half-open: touching isn't overlapping
    assert match_highlight(spans, 300, 0, 10) is None  # different snippet


# --- AI review persistence (criteria 1 & 2) -----------------------------------------


def test_ai_evidence_is_linked_to_any_overlapping_highlight_and_starred_are_covered():
    conv = 12
    s1, s2, s3 = _long_snippets(conv)
    db = PrototypeSession()
    try:
        rq_id = _rq(db, "provenance rq")
        starred_cited = _highlight(db, conv, s1, 0, 6, starred=True)
        plain_cited = _highlight(db, conv, s2, 2, 8, starred=False)
        starred_uncited = _highlight(db, conv, s3, 10, 15, starred=True)
        vm = _voice_memo(db, conv)

        result = {
            "extracted_interests": [],
            "connections": [
                {
                    "research_question_id": rq_id,
                    "insight_text": "an insight",
                    "confidence": "medium",
                    "rationale": "r",
                    "reflection_quote_start_word": None,
                    "reflection_quote_end_word": None,
                    "evidence": [
                        {"snippet_id": s3, "start_index": 0, "end_index": 3},  # unhighlighted
                        {"snippet_id": s2, "start_index": 0, "end_index": 4},  # overlaps plain
                        {"snippet_id": s1, "start_index": 4, "end_index": 12},  # overlaps starred
                        {"snippet_id": s1, "start_index": 0, "end_index": 99_999},  # invalid
                    ],
                }
            ],
        }
        [conn] = persist_review_result(
            prototype_db=db, cortico_db=CorticoSession(), voice_memo=vm, result=result, prompt="p", config=config
        )
        db.refresh(conn)
        rows = [(e.snippet_id, e.highlight_id, e.source) for e in conn.evidence]
        # Starred highlight first, then the user's other highlight, then AI-only text.
        assert rows == [(s1, starred_cited, "user"), (s2, plain_cited, "user"), (s3, None, "ai")]
        vm_id = vm.id
    finally:
        db.close()

    review = client.get(f"/voice_memos/{vm_id}/review").json()
    badges = [(e["highlight_id"], e["source"]) for e in review["connections"][0]["evidence"]]
    assert badges == [(starred_cited, "user"), (plain_cited, "user"), (None, "ai")]

    unassigned = {h["highlight_id"] for h in review["starred_unassigned"]}
    assert starred_cited not in unassigned  # cited by the AI, so not offered again
    assert starred_uncited in unassigned  # never mentioned, deterministically surfaced


def test_starred_cited_only_by_a_rejected_or_unmapped_connection_is_still_unassigned():
    conv = 13
    s1, s2, _ = _long_snippets(conv)
    db = PrototypeSession()
    try:
        rq_id = _rq(db, "rejected rq")
        in_rejected = _highlight(db, conv, s1, 0, 5, starred=True)
        in_unmapped = _highlight(db, conv, s2, 0, 5, starred=True)
        vm = _voice_memo(db, conv)
        for rq, hid, sid, status in ((rq_id, in_rejected, s1, "rejected"), (None, in_unmapped, s2, "suggested")):
            c = ReflectionConnection(
                voice_memo_id=vm.id, research_question_id=rq, insight_text="x", source="ai", status=status
            )
            db.add(c)
            db.flush()
            db.add(ConnectionEvidence(connection_id=c.id, highlight_id=hid, snippet_id=sid, start_index=0, end_index=5, source="user"))
        db.commit()
        vm_id = vm.id
    finally:
        db.close()

    unassigned = {h["highlight_id"] for h in client.get(f"/voice_memos/{vm_id}/review").json()["starred_unassigned"]}
    assert {in_rejected, in_unmapped} <= unassigned


# --- review-step assignment + manual adds (criterion 3) ------------------------------


def test_assigning_a_starred_highlight_in_review_files_it_with_highlight_evidence():
    conv = 14
    s1, s2, _ = _long_snippets(conv)
    db = PrototypeSession()
    try:
        rq_id = _rq(db, "assign rq")
        starred = _highlight(db, conv, s1, 3, 9, starred=True)
        plain = _highlight(db, conv, s2, 0, 4, starred=False)
        vm_id = _voice_memo(db, conv).id
    finally:
        db.close()

    review = client.get(f"/voice_memos/{vm_id}/review").json()
    offered = next(h for h in review["starred_unassigned"] if h["highlight_id"] == starred)

    body = {
        "decisions": [
            {   # the review step's "assign to RQ" control
                "connection_id": None,
                "action": "accept",
                "research_question_id": rq_id,
                "insight_text": "starred passage, assigned",
                "evidence": [
                    {**{k: s[k] for k in ("snippet_id", "start_index", "end_index")}, "highlight_id": starred, "source": "user"}
                    for s in offered["snippets"]
                ],
            },
            {   # a manual add citing a passage without saying it's a highlight
                "connection_id": None,
                "action": "accept",
                "research_question_id": rq_id,
                "insight_text": "manual add",
                "evidence": [{"snippet_id": s2, "start_index": 2, "end_index": 6, "source": "ai"}],
            },
        ]
    }
    filed = client.post(f"/voice_memos/{vm_id}/file", json=body).json()
    evidence = {c["insight_text"]: c["evidence"] for c in filed["connections"]}
    assert [(e["highlight_id"], e["source"]) for e in evidence["starred passage, assigned"]] == [(starred, "user")]
    assert [(e["highlight_id"], e["source"]) for e in evidence["manual add"]] == [(plain, "user")]

    assert starred not in {h["highlight_id"] for h in client.get(f"/voice_memos/{vm_id}/review").json()["starred_unassigned"]}

    memo = client.get("/memo").json()
    memo_unassigned = {h["highlight_id"] for g in memo["starred_unassigned"] for h in g["highlights"]}
    assert starred not in memo_unassigned
    section = next(s for s in memo["sections"] if s["research_question_id"] == rq_id)
    entry = next(e for e in section["entries"] if e["insight_text"] == "starred passage, assigned")
    assert entry["evidence"][0]["highlight_id"] == starred
    assert entry["evidence"][0]["starred"] is True


def test_highlight_from_another_conversation_is_refused():
    conv = 15
    s1, _, _ = _long_snippets(conv)
    other_s, _, _ = _long_snippets(12)
    db = PrototypeSession()
    try:
        foreign = _highlight(db, 12, other_s, 0, 3, starred=True)
        vm_id = _voice_memo(db, conv).id
    finally:
        db.close()
    body = {
        "decisions": [
            {
                "connection_id": None,
                "action": "accept",
                "insight_text": "bad",
                "evidence": [{"highlight_id": foreign, "snippet_id": s1, "start_index": 0, "end_index": 3}],
            }
        ]
    }
    assert client.post(f"/voice_memos/{vm_id}/file", json=body).status_code == 400


# --- memo-page edits keep the link (criterion 1, memo path) ---------------------------


def test_memo_evidence_edit_keeps_highlight_link():
    conv = 16
    s1, s2, _ = _long_snippets(conv)
    db = PrototypeSession()
    try:
        rq_id = _rq(db, "memo edit rq")
        starred = _highlight(db, conv, s1, 0, 5, starred=True)
        vm = _voice_memo(db, conv)
        c = ReflectionConnection(
            voice_memo_id=vm.id, research_question_id=rq_id, insight_text="filed", source="ai", status="accepted"
        )
        db.add(c)
        db.flush()
        db.add(ConnectionEvidence(connection_id=c.id, highlight_id=starred, snippet_id=s1, start_index=1, end_index=4, source="user"))
        db.add(ConnectionEvidence(connection_id=c.id, snippet_id=s2, start_index=0, end_index=3, source="ai"))
        db.commit()
        conn_id = c.id
    finally:
        db.close()

    section = next(s for s in client.get("/memo").json()["sections"] if s["research_question_id"] == rq_id)
    [entry] = section["entries"]
    # The memo page removes the AI passage and sends the rest back, as an older client
    # would, without highlight_id: the server re-links it by overlap.
    kept = [{k: v for k, v in e.items() if k != "highlight_id"} for e in entry["evidence"] if e["source"] == "user"]
    assert client.patch(f"/memo/connections/{conn_id}", json={"evidence": kept}).status_code == 200

    section = next(s for s in client.get("/memo").json()["sections"] if s["research_question_id"] == rq_id)
    [entry] = section["entries"]
    assert [(e["highlight_id"], e["source"], e["starred"]) for e in entry["evidence"]] == [(starred, "user", True)]
    memo_unassigned = {h["highlight_id"] for g in client.get("/memo").json()["starred_unassigned"] for h in g["highlights"]}
    assert starred not in memo_unassigned
