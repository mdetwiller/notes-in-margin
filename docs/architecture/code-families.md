# Code families

Code families are broad parent themes per RQ, synthesized from that RQ's filed memo entries.
They are owned by `backend/app/services/code_families.py` and served by
`backend/app/routers/code_families.py`. The cap and merges aren't in `docs/prd-phase-2.md`;
they come from resolving its granularity question (`docs/prototype-log.md`).

## Statuses

- **Families:** `suggested`, `accepted`, `dismissed`, `merged`. Only the first two are live:
  `LIVE_FAMILY_STATUSES = ("suggested", "accepted")`.
- **Members** must be filed connections in the same RQ, where filed means
  `FILED_STATUSES = ("accepted", "edited")`. This tuple is duplicated in `routers/memo.py`;
  change both together.
- The frontend's status unions are in `frontend/src/lib/types.ts`.

## Cap (`config.code_families` in `backend/config.yaml`)

| Key | Value | Meaning |
|---|---|---|
| `max_per_rq` | 5 | Maximum live families per RQ, unless the user overrides it |
| `near_cap_at` | 4 | At or above this many live families, synthesis also proposes merges |
| `max_new_per_run` | 2 | New families one run may create, even with `override_cap=true` |

- `cap_status(live_count, limits, override_cap)` computes what a run may do.
  `_apply_family_results` enforces it server-side, whatever the model returned.
- `GET /research_questions/{rq_id}/code_families/state` reports the cap.
  `test_code_families.py` asserts `max_per_rq: 5` from the real config, so changing the
  config value means updating that test.

## Synthesis and merges

- `synthesize_code_families` skips the model call when the RQ has nothing filed.
- `_apply_family_results` attaches members to existing families or creates new ones. Only
  valid connection ids are kept (`_valid_connection_ids`).
- `_apply_merge_suggestions` runs only near the cap. It needs 2 or more live family ids, and
  skips a set that already has a pending suggestion.
- `accept_merge` re-checks that every source family is still live (the router returns 409
  if not). The target is the accepted family if there is one, else the oldest
  (`_merge_target`). The source families move to `merged`; nothing is deleted.
- Assigning codes to individual highlights or snippets is out of scope
  (`docs/prd-phase-2.md`).
