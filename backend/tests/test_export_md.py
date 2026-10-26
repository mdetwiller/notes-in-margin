"""The backup script must never overwrite an earlier export, and its database copy must be
a complete, readable SQLite file."""
import importlib.util
import os
import sqlite3
from pathlib import Path

from app.config import get_config
from app.db import CorticoSession, PrototypeSession
from app.models_prototype import VoiceMemo

_spec = importlib.util.spec_from_file_location(
    "export_md", Path(__file__).resolve().parent.parent / "scripts" / "export_md.py"
)
export_md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export_md)


def _make_voice_memo() -> int:
    db = PrototypeSession()
    try:
        vm = VoiceMemo(
            user_id=101,
            conversation_id=9,
            audio_path="db/local/audio/test.webm",
            duration=65.0,
            transcription_edited="an exported reflection",
            status="ready_for_review",
        )
        db.add(vm)
        db.commit()
        return vm.id
    finally:
        db.close()


def test_export_writes_memo_and_transcripts(tmp_path):
    vm_id = _make_voice_memo()
    exports = tmp_path / "exports"
    with CorticoSession() as cortico_db, PrototypeSession() as prototype_db:
        n_transcripts = export_md.write_transcripts(exports, cortico_db, prototype_db)
        export_md.write_memo(exports, cortico_db, prototype_db)

    assert n_transcripts >= 1
    (transcript,) = exports.glob(f"transcripts/*_voice-memo-{vm_id}.md")
    text = transcript.read_text()
    assert "an exported reflection" in text
    assert "**Length:** 1:05" in text
    assert (exports / "memo.md").read_text().startswith("# Memo")


def test_previous_export_is_moved_aside_not_overwritten(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "memo.md").write_text("first")
    os.utime(exports / "memo.md", (1761400000, 1761400000))

    first = export_md.archive_previous_export(exports)
    exports.mkdir()
    (exports / "memo.md").write_text("second")
    os.utime(exports / "memo.md", (1761400000, 1761400000))
    second = export_md.archive_previous_export(exports)

    assert not exports.exists()
    assert first != second
    assert (first / "memo.md").read_text() == "first"
    assert (second / "memo.md").read_text() == "second"
    assert export_md.archive_previous_export(exports) is None


def test_database_backup_is_a_complete_copy(tmp_path):
    _make_voice_memo()
    source = get_config().prototype_db_abspath
    target = export_md.backup_database(source, tmp_path)

    with sqlite3.connect(target) as copy, sqlite3.connect(f"file:{source}?mode=ro", uri=True) as live:
        assert copy.execute("pragma integrity_check").fetchone() == ("ok",)
        assert (
            copy.execute("select count(*) from voice_memo").fetchone()
            == live.execute("select count(*) from voice_memo").fetchone()
        )


def test_database_backups_never_overwrite_each_other(tmp_path):
    source = get_config().prototype_db_abspath
    first = export_md.backup_database(source, tmp_path)
    second = export_md.backup_database(source, tmp_path)
    assert first != second
    assert first.exists() and second.exists()
