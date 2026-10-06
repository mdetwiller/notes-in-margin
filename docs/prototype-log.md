# Prototype log

Running record of every place this prototype's build diverges from the PRD
(`docs/prd-reflective-listening.md`), per its own instruction to follow `schema.sql` and
note the difference. Entries are added as they're hit, not just up front.

## File locations

- The task referenced `docs/prd-reflective-listening.md` and `db/schema.sql`, neither of
  which existed. The actual PRD was at the repo root as
  `PRD Reflective Listening Prototype (Transcript Reader + Voice Memo).md` — moved to
  `docs/prd-reflective-listening.md`.
- `db/schema.sql` didn't exist either. What existed was `acp_pipeline_snapshot.db`, a live
  SQLite snapshot (not a schema-only pg_dump as the PRD describes — it has data, and it's
  SQLite rather than Postgres). `db/schema.sql` is generated from this snapshot
  (`sqlite3 acp_pipeline_snapshot.db ".schema"`) and treated as the PRD's "source of truth
  for names." The snapshot file itself stays gitignored, as the PRD requires.
- The repo was not a git repository yet — initialized as part of scaffolding.

## Table/column naming deltas (schema.sql wins per the PRD)

- **`highlight` name collision:** Cortico already owns a real, read-only `highlight` table
  (and an unrelated prior prototype's `solo*` tables — sensemaking sessions, codebooks,
  tagging runs — not part of this PRD). This prototype's own highlight table is named
  **`rl_highlight`** instead, following the existing `solo_`-prefix convention in the same
  database for prototype-owned tables.
- **No `snippet.uuid`:** snippets have integer `id`/`cortico_id`, no UUID column. Every PRD
  field named `snippet_uuid` is **`snippet_id`** (integer) instead, in `highlight_snippet`,
  `connection_evidence`, `section_checkpoint`, and the assembled memo view.
- **Snippet field names:** `text` not `content`; `order_index` not `index_in_conversation`.
  Speaker name and facilitator-ness come from joining `participant` via
  `snippet.participant_id`, not inline snippet columns. Unused-but-available extra columns:
  `is_facilitator_prompt`, `is_mechanical`, `ai_score`.
- **`words` shape:** a JSON array of `{"word","start","end","confidence"}` objects, not
  `[word, start, end, confidence]` tuples as the PRD's mock data shows. `voice_memo`'s
  Whisper output is stored in the same dict shape for consistency with Cortico, not the
  tuple shape from the PRD's example.
- **Guide linkage is real but unused in this data:** `conversation.conversation_guide_id`
  exists, but is `NULL` for all 201 conversations in the snapshot, including project 5's
  (the only project with an actual `conversationguide` row). So the fallback the PRD already
  anticipated — project's latest guide version — is the path actually exercised:
  `conversation.conversation_guide_id` if set, else the highest-`version` `conversationguide`
  row for `conversation.project_id`. There's no `published`/status flag on `conversationguide`,
  so "latest" = max `version`.
- **Conversation guide is 3 relational tables**, not one nested `sections[].prompts[]` blob:
  `conversationguide` → `guidesection` → `guidequestion` (`text`, `shorthand_code`,
  `order_index`).
- **Conversation fields:** no `start_time` (conversation list ordering uses `id` instead);
  has `duration_seconds`, `is_open`, `facilitator_participant_id`; singular `language`, not
  `language_codes`.
- **No Postgres roles/schemas:** the snapshot is SQLite. The PRD's "SELECT-only role +
  separate schema" read-only enforcement is replaced with an app-layer equivalent: a
  dedicated read-only SQLAlchemy engine (`mode=ro&immutable=1`) for Cortico tables that never
  has `add`/`commit` called against it anywhere in the codebase, and a second, separate
  SQLite file (`db/prototype.db`) for everything prototype-owned.
- **Dropped speculative `rl_highlight` fields:** the PRD lists `type`, `tool_id`, `metadata`
  as mirroring Cortico's `CreateHighlightSchema` for future promotion, but that schema isn't
  in our ground truth and no screen or behavior in this PRD reads or writes them. Left out
  rather than carried as unused columns.
- **Added `app_setting` (key/value) table**, not in the PRD's data model: needed to persist
  the editable AI-review prompt (view/save/reset-to-default) across restarts.

## Scoping decisions (confirmed with the user, not schema deltas)

- Only project 5 (conversation ids 9, 10) has a real `conversationguide` row in this
  snapshot (1 of 54 projects). Transcript switching in this build is scoped to those two
  conversations so section checkpoints are actually exercisable; widening is a one-line
  filter change later.
- Every conversation's `audio_url` is null/empty (0 of 201). Playback and word-level
  "karaoke" highlighting are built against the real `audio_url` + `words` offset contract,
  but degrade to a plain-text view with no player when `audio_url` is empty — which is
  always, for now, until a real audio file is supplied for one conversation.
- Model ID/params verified against OpenAI's own docs (`developers.openai.com`,
  `help.openai.com`) on 2026-10-05: `gpt-5.6-luna` is real and supports
  `reasoning.effort: low`.

## Implementation notes

- **PyAV pin:** `faster-whisper` needs `av` pinned to `13.1.0` — the latest `av` (19.x)
  removed the `metadata_errors` kwarg its decoder call uses. Pinned in
  `backend/requirements.txt`.
- **Test isolation:** backend tests point `PROTOTYPE_DB_PATH` at a scratch file
  (`tests/conftest.py`), so `pytest` never leaves rows in the real `db/prototype.db`. The
  Cortico snapshot is still queried for real in tests (guide resolution, evidence
  validation) — only the prototype-owned tables are redirected.
- **`uvicorn --reload` leaves orphaned workers:** its child process doesn't show "uvicorn"
  in its command line, so `pkill -f uvicorn` can miss it and leave a zombie holding the
  port. Kill by port (`lsof -ti:8000 | xargs kill -9`) if restarts seem to serve stale data;
  the dev server in this repo is run without `--reload` for that reason.
- **AI review is unverified against a live model call** — no `OPENAI_API_KEY` was available
  in this environment. The structural-validation and filing logic is covered by tests and
  by manually exercising every other endpoint against real data; only the actual
  `gpt-5.6-luna` round trip is unverified. Add `backend/.env` with `OPENAI_API_KEY=...` to
  enable it (python-dotenv loads it automatically).
- **Full voice→transcript pipeline verified with real audio:** generated a synthetic
  reflection with macOS `say`, uploaded it through `POST /conversations/9/voice_memos`, and
  confirmed `faster-whisper` returned an accurate, correctly word-timestamped transcription
  in the exact `{word,start,end,confidence}` shape Cortico uses.
