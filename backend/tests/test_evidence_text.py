"""Against the real, read-only Cortico snippet data — confirms word-index spans resolve
to the actual quoted text, which is what the review and memo screens now show instead of
a bare snippet id."""
import json

from app.db import CorticoSession
from app.evidence_text import quoted_texts
from app.models_cortico import Snippet


def test_quoted_texts_resolves_real_snippet_words():
    db = CorticoSession()
    try:
        snippet = db.query(Snippet).filter(Snippet.conversation_id == 9).first()
        words = json.loads(snippet.words)
        expected = " ".join(w["word"] for w in words[0:3])

        result = quoted_texts(db, [(snippet.id, 0, 3)])
        assert result[(snippet.id, 0, 3)] == expected
    finally:
        db.close()


def test_quoted_texts_batches_multiple_spans_in_one_query():
    db = CorticoSession()
    try:
        snippets = db.query(Snippet).filter(Snippet.conversation_id == 9).limit(2).all()
        spans = [(s.id, 0, 1) for s in snippets]
        result = quoted_texts(db, spans)
        assert len(result) == 2
        for s in snippets:
            words = json.loads(s.words)
            assert result[(s.id, 0, 1)] == words[0]["word"]
    finally:
        db.close()


def test_empty_spans_returns_empty_dict():
    db = CorticoSession()
    try:
        assert quoted_texts(db, []) == {}
    finally:
        db.close()
