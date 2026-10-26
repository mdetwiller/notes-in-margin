# LLM and transcription calls

## Provider and configuration

- **SDK:** `openai==3.24.0`. Clients are created with `OpenAI()` and no arguments, so they
  read `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the environment. `backend/app/config.py`
  loads both from `backend/.env`.
- **API:** the Responses API, `client.responses.create(...)`, with
  `text={"format": {"type": "json_schema", "strict": True, ...}}`.
- **Model:** `ai_review.model: "gpt-5.6-luna"` and `reasoning_effort: "low"` in
  `backend/config.yaml`. Both were checked against OpenAI's docs on 2026-10-05
  (`docs/prototype-log.md`).
- **Timeouts and retries:** none are set, so the SDK defaults apply.
- **Errors:** exceptions are not caught, so an OpenAI failure reaches the client as a bare
  500. This is a known gap.

## Call sites

| Function | Output schema name and shape | Checks after the model returns |
|---|---|---|
| `generate_connections` and `persist_review_result` (`services/ai_review.py`) | `reflection_review`: `{connections: [{research_question_id or null, insight_text, confidence, rationale, reflection_quote_start_word, reflection_quote_end_word, evidence: [{snippet_id, start_index, end_index}]}], extracted_interests: [str]}` | `_validate_evidence_in_range` keeps only evidence whose snippet exists, is in this conversation, and has `0 <= start < end <= word_count`; invalid evidence is dropped. Evidence is linked with `resolve_evidence`, ordered starred highlight first, then other highlights, then AI-only text. Duplicate spans are dropped. |
| `generate_next_step_suggestions` (`services/next_steps.py`) | `next_step_suggestions`: `{suggestions: [{research_question_id, suggested_direction, recommended_conversation_id, rationale}]}` | A conversation id not found in Cortico becomes null. An RQ id that isn't an active RQ becomes null. A row with neither a direction nor a conversation is skipped. |
| `synthesize_code_families` (`services/code_families.py`) | `code_families`: `{families: [{existing_family_id, name, definition, member_connection_ids}], merge_suggestions: [{family_ids, name, definition, rationale}]}` | Members must be filed connections in this RQ (`_valid_connection_ids`). The cap is applied server-side. The model call is skipped when nothing is filed. See `code-families.md`. |
| `backfill` (`scripts/backfill_gists.py`) | `conversation_gist`: `{summary, keywords}` | Effort is pinned to `"low"`. Rows that already exist are skipped, and it commits per conversation, so it can resume. |

## Rules

- Every AI-written row has `status="suggested"` and `ai_metadata` (`model`,
  `reasoning_effort`, `prompt`, plus `confidence`, `rationale` and `reflection_timestamp`
  for connections). Only user actions move a row past suggested.
- Model ids and effort come from `config.ai_review`. The single deliberate exception is the
  gist backfill's `"low"` pin.
- The review prompt can be edited. It is stored in `app_setting` under `"review_prompt"`
  (`get_review_prompt`, `set_review_prompt`, `reset_review_prompt`), with
  `DEFAULT_REVIEW_PROMPT` as the fallback.
- The gist backfill is not an endpoint and is not triggered from the UI, by decision
  (`docs/prd-phase-2.md`). It makes about 200 paid calls; the measured run took 720.7 s for
  198 calls, with 279,579 input and 29,813 output tokens.

## Transcription

- `services/transcription.py:transcribe` uses local faster-whisper (`small.en`, `int8`) and
  makes no API call. `_get_model` is cached with `lru_cache`, and the import is lazy, so
  tests never load the model.
- It runs in a daemon thread started by `POST /conversations/{id}/voice_memos`. Status goes
  `recorded` → `transcribing` → `ready_for_review` or `failed` (with `transcription_error`
  set) → `filed`. The frontend polls every 700 ms (`ReflectionPanel.tsx`).
- Words are stored as `[{word, start, end, confidence}]` dicts to match Cortico's
  `snippet.words`.
- Keep `av==13.1.0`, because 19.x breaks faster-whisper.
