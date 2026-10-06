"""Structural validation of AI-proposed evidence against the real snapshot — this is the
automated half of the PRD's open "how are outputs validated" question (the human review
step is the other half)."""
import json

from app.db import CorticoSession
from app.models_cortico import Snippet
from app.services.ai_review import _validate_evidence_in_range


def test_valid_evidence_within_a_real_snippet_passes():
    db = CorticoSession()
    try:
        snippet = db.query(Snippet).filter(Snippet.conversation_id == 9).first()
        word_count = len(json.loads(snippet.words))
        assert _validate_evidence_in_range(db, 9, snippet.id, 0, min(3, word_count))
    finally:
        db.close()


def test_out_of_range_word_indices_are_rejected():
    db = CorticoSession()
    try:
        snippet = db.query(Snippet).filter(Snippet.conversation_id == 9).first()
        word_count = len(json.loads(snippet.words))
        assert not _validate_evidence_in_range(db, 9, snippet.id, 0, word_count + 1000)
    finally:
        db.close()


def test_snippet_from_a_different_conversation_is_rejected():
    db = CorticoSession()
    try:
        snippet = db.query(Snippet).filter(Snippet.conversation_id == 10).first()
        assert not _validate_evidence_in_range(db, 9, snippet.id, 0, 1)
    finally:
        db.close()


def test_nonexistent_snippet_is_rejected():
    db = CorticoSession()
    try:
        assert not _validate_evidence_in_range(db, 9, 999_999_999, 0, 1)
    finally:
        db.close()
