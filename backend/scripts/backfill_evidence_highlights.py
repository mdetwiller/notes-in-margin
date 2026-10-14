"""One-time backfill of `connection_evidence.highlight_id` for evidence written before
every evidence path linked passages to the user's highlights (see app/evidence_provenance.py
and docs/prototype-log.md, 2026-10-14).

Additive only: it touches rows whose highlight_id is null, and only sets highlight_id (and
source="user", which is what a linked passage is) when the passage overlaps one of the
user's highlights on that conversation. No row is deleted and no linked row is changed, so
it's safe to re-run. The connection's own ai_metadata still records that the AI proposed it.

Run from backend/: `python scripts/backfill_evidence_highlights.py --dry-run` to preview,
then without --dry-run. Point PROTOTYPE_DB_PATH at a copy first to try it out.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import PrototypeSession  # noqa: E402
from app.evidence_provenance import highlight_spans, match_highlight  # noqa: E402
from app.models_prototype import ConnectionEvidence, ReflectionConnection, VoiceMemo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report matches without writing")
    args = parser.parse_args()

    db = PrototypeSession()
    try:
        rows = (
            db.query(ConnectionEvidence, VoiceMemo)
            .join(ReflectionConnection, ConnectionEvidence.connection_id == ReflectionConnection.id)
            .join(VoiceMemo, ReflectionConnection.voice_memo_id == VoiceMemo.id)
            .filter(ConnectionEvidence.highlight_id.is_(None))
            .all()
        )
        spans_cache: dict[tuple[int, int], list] = {}
        linked = 0
        for ev, vm in rows:
            key = (vm.user_id, vm.conversation_id)
            if key not in spans_cache:
                spans_cache[key] = highlight_spans(db, *key)
            match = match_highlight(spans_cache[key], ev.snippet_id, ev.start_index, ev.end_index)
            if match is None:
                continue
            linked += 1
            print(
                f"evidence {ev.id} (snippet {ev.snippet_id} [{ev.start_index},{ev.end_index})) "
                f"-> highlight {match.highlight_id}{' (starred)' if match.starred else ''}"
            )
            if not args.dry_run:
                ev.highlight_id = match.highlight_id
                ev.source = "user"

        print(f"{len(rows)} unlinked evidence rows, {linked} overlap a highlight"
              + (" (dry run, nothing written)" if args.dry_run else " — linked"))
        if not args.dry_run:
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
