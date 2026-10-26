# Review, filing, memo and evidence

## Flow

1. The user highlights passages (`rl_highlight` and `highlight_snippet`) and records a
   voice memo, which is then transcribed.
2. `POST /voice_memos/{id}/review` (`run_review`) calls `generate_connections`, then
   `persist_review_result`, which saves the proposals as `status="suggested"`. On resume,
   the frontend calls `GET /voice_memos/{id}/review` instead of running the review again.
3. The review step (`frontend/src/components/ReviewStep.tsx`) lets the user accept, edit or
   reject each proposal, add a connection the AI missed, and assign each starred,
   unassigned highlight to an RQ.
4. "File to memo" sends everything to `POST /voice_memos/{id}/file` (`file_to_memo`). This is
   the only route that sets a connection to `accepted` or `edited`. Rejected proposals stay,
   with `status="rejected"`.
5. The memo page (`GET /memo`) shows filed connections, where filed means
   `FILED_STATUSES = ("accepted", "edited")`. The user can edit an entry (insight text and
   evidence) or retract it.

## Evidence provenance (`backend/app/evidence_provenance.py`)

`connection_evidence.highlight_id` makes a passage "yours". It drives the `yours` or
`AI-suggested` badge in review, the starred flag on the memo, and whether a starred highlight
counts as assigned.

- **Every evidence write goes through `resolve_evidence`.** AI review calls it directly.
  Review adds and edits (`routers/review.py`) and memo edits (`routers/memo.py`) call
  `evidence_row`, which keeps an explicit `highlight_id` and otherwise links by overlap.
  `evidence_row` returns 400 for a `highlight_id` that belongs to another user or
  conversation.
- **Matching is by overlap.** A span links to the user highlight it overlaps on the same
  snippet. Spans are half-open `[start_index, end_index)`, and any shared word counts. Ties
  go to the starred highlight, then the larger overlap, then the older highlight
  (`match_highlight`). A linked span gets `source="user"`; an unlinked one keeps its source.
- **"Starred, unassigned"** comes only from `assigned_highlight_ids`. A starred highlight
  counts as assigned only when it is cited by a connection that has an RQ and isn't
  rejected or retracted. Review and memo both use it.
- **Backfill for older rows:** `backend/scripts/backfill_evidence_highlights.py` (supports
  `--dry-run`). It only sets `highlight_id` and `source` on rows where `highlight_id` is null
  and the span overlaps a highlight, so it is safe to re-run. The user runs it on the dev
  database.

## Editing and provenance

- Every edit (`file_to_memo` with action `edit`, and `edit_memo_entry`) first writes a
  `ReflectionConnectionRevision` snapshot (which includes `highlight_id`), then sets
  `source="user"` and `edited_from_ai=True`.
- Retracting sets a status and never deletes, so the memo's history stays intact.
- `quoted_texts` (`backend/app/evidence_text.py`) turns `(snippet_id, start, end)` spans
  into text with one batched Cortico query, and returns `""` for a missing snippet.
- Memo evidence links go to `/?conversation=N&snippet=ID`. `ReaderPage` scrolls to that
  snippet and outlines it.

## Highlights

- `create_highlight` takes `project_id` from the Cortico conversation, never from
  `config.default_project_id`. That was a regression, and `tests/test_highlights.py`
  guards it.
- RQs still use `config.default_project_id` (`research_questions.py` and `seed.py`).
