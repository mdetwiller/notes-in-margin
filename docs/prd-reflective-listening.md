# PRD: Reflective Listening Prototype (Transcript Reader + Voice Memo)

Oct 5, 2026 · @Maya

## Overview and goals

This prototype adds a spoken reflection step to a transcript reader, so a sensemaker's evidence-linked reflections build up into a running memo per research question (RQ). AI does the labor; the human keeps the judgment.

Builds on: a minimalist recreation of Om Zugo's Medium-style reader. His code is not available, so the agent rebuilds the reader from this description. It has: filtered conversation transcripts, audio playback, highlights with margin memos, hover navigation by guide question, and switching between transcripts.&#32;

What is new: when a user reaches the end of a transcript, they record a voice reflection anchored by their own RQs and by AI reflection questions. They review and approve the transcription and the AI's proposed RQ connections. Approved reflections are filed, with their evidence, into a running RQ memo.

**Goals**

- Test whether a spoken reflection, alongside typed margin notes, yields richer evidence-linked insight per RQ.
- Keep the user in control: nothing enters the memo without explicit approval, and AI-proposed items are always visibly distinct from the user's own.
- Mirror Cortico V2 shapes and IDs, read-only, so prototype data can later be promoted into the platform.
- Keep an audit trail from every memo entry to its transcript passages and its voice recording.

**Non-goals this round:** corpus-wide pointing to related material, cross-person or AI-vs-human memo comparison, and multi-user support (see Follow-up work).

## Users, context, and scope

The target users are lay sensemakers from communities across the US who listen to conversation transcripts one at a time. For this round the only tester is the prototype's author, working from local test data.

| Area | In scope | Out of scope (follow-up) |
| --- | --- | --- |
| Reading | Transcript reader with highlights, margin memos, starring, section navigation, transcript switching | Corpus-wide search or browsing |
| RQs | Seeded from a config file; editable in the side panel while reading | Team-shared or negotiated RQs |
| Reflection | End-of-transcript prompt; docked voice-memo panel with anchors; Whisper transcription; saved audio | Real-time or live transcription |
| AI review | Proposed RQ connections and evidence passages; approve, edit, or reject before filing | AI suggestions of new directions from "what I want to hear next"; pointing to other places in the corpus via topic mapping |
| Memo | Running RQ memo: full page plus compact side-panel view | Convergence and divergence across people's and the AI's memos on the same transcript |
| Data | Read Cortico data; prototype-owned V2-shaped tables | Writing back to Cortico; multi-user accounts |

## Foundation: the recreated reader and what is new

Om Zugo's reader code is not available to the coding agent, so it should not search for it. It should build a minimal reader from the description below.

**Recreate (minimal version)**

- Medium-style, minimalist transcript page showing a filtered conversational transcript with speaker turns sectioned by conversation guide question.
- Highlight a passage, then start typing to leave a memo in the margin beside it.
- Left menu, visible on hover, that jumps between sections. Sections now come from the user's own checkpoints (see Section checkpoints) instead of automatic detection.
- Switching between transcripts.

* Basic audio playback of the conversation, using `audio_url` and the snippet audio offsets.
* Keep it minimal: a single column of speaker turns, readable typography, and only the behaviors above. Visual polish is out of scope.

**Add in this prototype**

- Starring a highlight to guarantee it is cited as evidence.
- A side panel holding the RQ list and the compact memo view.
- End-of-transcript detection and prompt.
- A docked reflection panel for recording a voice memo.
- A review step for transcription and proposed RQ connections.
- A full-page running RQ memo.

**Note for the agent:** Om's code is not available, so do not look for it. Persist highlights, margin memos, and checkpoints directly in the prototype-owned tables in the data model section.

## End-to-end flow

One pass through a transcript takes the user from listening to an approved memo entry.

1. The user opens a transcript, optionally marks sections with checkpoints and jumps between them, and reads or listens. The user can listen at 1x, 1.5x, or 2x speed and there's a karaoke style light up of each spoken word as the audio plays.
2. They highlight passages, type margin memos, and star the highlights they most want cited.
3. They can edit their RQs in the side panel at any time.
4. On reaching the end of the transcript, a prompt invites them to reflect.
5. They open the docked reflection panel. It shows their RQs, the AI's reflection questions, their highlights and memos for this transcript, and the full transcript, scrollable.
6. They record a voice memo. The audio is saved, then transcribed with Whisper.
7. The review step shows the transcription next to the AI's proposed RQ connections and evidence passages.
8. For each connection the user accepts, edits, or rejects it. They can also edit the transcription.
9. On approval, the entry is appended to the matching RQ sections of the running memo, citing the transcript and passages.
10. The user can open the full memo page, or glance at the compact memo in the side panel while reading the next transcript.

**Reflection questions the AI offers as anchors**

- What do I think I learned?
- How do I know? Which examples in the conversation do I point to?
- What surprised me?
- What would be interesting or helpful to hear next?

The user's own RQs are always shown alongside these.

## Screens and interactions

### 1. Reader (minimal recreation of Om's reader)

- Highlight and margin-memo behavior stays as built. Add a star toggle on each highlight.
- Starred highlights are visually marked and are always included as candidate evidence in AI review.
- A side panel opens from the page edge with two tabs: **RQs** and **Memo**.

### 2. RQ panel (side panel tab)

- Lists the user's RQs, seeded from a config file at startup.
- The user can add, edit, reorder, and archive RQs at any time. Edits are saved immediately.
- Archived RQs stay attached to past memo entries but are not offered for new connections.

### 3. End-of-transcript prompt

- Appears once when the user scrolls to the end of the active transcript, as a non-blocking inline card with a "Reflect on this conversation" action and a "Not now" dismiss.
- Dismissing does not lose anything. If the user tries to open another transcript after reaching the end of this one without recording a reflection, a confirmation dialog asks: "Are you sure you want to leave this transcript without recording your reflections?" It offers "Reflect now", which opens the reflection panel, and "Leave anyway", which continues to the other transcript.

### 4. Docked reflection panel

- Opens beside the reader rather than replacing it, so the user can scroll the transcript while recording.
- Shows: the user's RQs; the four AI reflection questions; the user's highlights and margin memos for this transcript (starred ones first); record, pause, stop, and re-record controls with an elapsed timer.
- Clicking a highlight in the panel scrolls the transcript to it.
- On stop, the audio is saved and transcription starts. The user sees progress, then moves to review.

* After filing, the user can record another voice memo for the same transcript from this panel. Its entries are appended after the earlier ones in the memo.

### 5. Review step

- Two columns: the editable transcription of the voice memo, and the AI's proposed RQ connections.
- Each proposed connection shows: the RQ, a short statement of the insight, the supporting passages, and a provenance badge on each passage (**yours** for the user's highlights, **AI-suggested** for others).
- Per connection: accept, edit (insight text and evidence list, including adding or removing passages), or reject.
- The user can also add a connection the AI missed.
- A single "File to memo" action writes only the accepted connections. Nothing is written to the memo before this action.

### 6. Memo page and side-panel memo

- Full page: one section per RQ, entries in chronological order, each showing the insight text, transcript title, evidence passages (clickable back to the transcript), the date, and a link to the voice recording and its transcription.
- Side panel: the same entries in a compact list, grouped by RQ, with click-through to the full page.
- Both read from the same data.

* Starred highlights not assigned to any RQ appear in a "Starred, unassigned" group for their transcript, so they are not lost. This is derived from `highlight.starred` and needs no extra table.

- The memo is a live doc. After filing, the user can edit an entry's insight text, add or remove its evidence passages, reorder entries within an RQ, and retract an entry. Retracted entries are hidden by default, not deleted.
- Editing AI-originated text changes its source to `user` and records `edited_from_ai`. Prior versions are kept, and every entry stays linked to its voice recording and original transcription.

### 7. Section checkpoints (navigation)

For now, the user marks sections by hand rather than the app detecting them.

- The conversation guide's questions (typically 5-6) are listed in the hover menu. Each shows as marked or unmarked for the active transcript.
- The user drops a checkpoint on a speaker turn (a snippet) and picks which guide question it starts. A section runs from its checkpoint to the next checkpoint or the end of the transcript.
- Each question has at most one checkpoint per transcript. Moving a checkpoint to another turn replaces the old one, and the user can delete it.
- Once checkpoints exist, the menu lists the marked questions in transcript order and jumps to them. Unmarked questions appear dimmed with a prompt to mark them.
- Checkpoints are the user's own annotations, stored in the prototype-owned `section_checkpoint` table.
- Assumption: V2 guides belong to a project and conversations carry no guide ID, so the reader uses the project's latest published guide version unless `schema.sql` shows a direct link.

## AI behavior

The AI proposes; the user decides. It never writes to the memo on its own.

**Inputs to the AI review call:** the voice memo transcription; the user's RQs; the full transcript (snippets with UUIDs and word indices); the user's highlights and margin memos for this transcript, with starred flags.

**Outputs:**

1. **RQ connections.** For each RQ the reflection bears on, a one-to-two sentence statement of the insight, written close to the user's own words, plus a confidence note. A reflection may map to several RQs or to none; an unmapped insight is surfaced as such rather than forced into an RQ.
2. **Evidence passages.** For each connection, the passages the reflection appears to draw on, as snippet UUID plus word indices. Rules:
   - Starred highlights are always included as candidates, even if the voice memo never mentions them. Uncited ones are offered in review for assignment to an RQ.
   - The user's other highlights are preferred over unhighlighted text.
   - Additional transcript passages may be proposed, each marked AI-suggested.
3. **Gaps and interests (captured, not acted on).** The user's "what I'd like to hear next" statements are extracted and stored on the memo entry. Suggesting new directions and pointing to other places in the corpus is follow-up work.

**Provenance rules**

- Every connection and every evidence passage carries a source: `user` or `ai`.
- If the user edits an AI-proposed item, it becomes `user` with `edited_from_ai` recorded.
- Rejected AI proposals are kept in the log with status `rejected` rather than deleted, so the review can be audited later.

**Prompting guardrails:** the AI must quote or point to the transcript and the user's words, not invent evidence; it must not state insights the user did not voice; and it should say so when the reflection does not clearly connect to any RQ.

**Model and editable prompt**

- The AI review uses OpenAI's GPT-5.6 Luna (`gpt-5.6-luna`) with reasoning effort `low`. Model ID and effort live in config, not code, so they can change without a rebuild.
- The review prompt is editable by the user in a simple settings view: it shows the current prompt, with save and reset-to-default actions. The next review uses the saved prompt.
- `ai_metadata` on each connection records the model, reasoning effort, and prompt text that produced it, so results can be compared across prompt edits.
- Before building, the agent should confirm the model ID and parameter names against OpenAI's current API reference.

## Voice capture and transcription

The prototype records in the browser and transcribes with Whisper, keeping the original audio.

- **Interface contract:** audio in, timestamped text out. Words use the same `[word, start, end, confidence]` shape as Cortico's `TranscriptSchema`, so Whisper output needs no conversion.
- **Recommended implementation:** a local Whisper run (for example whisper.cpp or faster-whisper) behind a small server route, which keeps test recordings off third-party servers. A hosted transcription API is an acceptable fallback if local setup is a blocker. The agent should record which it used.
- **Audio retention:** the original recording is saved and linked to its transcription, its review decisions, and the memo entries it produced. Store files outside git (a gitignored folder) and reference them by path in the database.
- **Editing:** the user can correct the transcription in the review step. Both the raw Whisper output and the edited text are stored.
- **Consent and retention:** while the only tester is the author, no extra consent flow is needed. Before real community members use it, add consent, a retention policy, and a delete-my-recording action. This PRD flags it; it does not specify it.

* **Maximum length:** 20 minutes per voice memo. The recorder shows elapsed time against the limit and stops automatically at 20 minutes.

## Data model

The prototype reads Cortico data and never writes to it. Everything new lives in prototype-owned tables whose field names, types, and integer IDs mirror Cortico V2, so rows can later be promoted into the platform with little translation.

**Source of truth for names:** `db/schema.sql`, a schema-only `pg_dump` of the existing Postgres database, to be added to the repo. The V2 object names below come from the Cortico V2 OpenAPI spec; where `schema.sql` disagrees on a table or column name, the agent should follow `schema.sql` and note the difference in the prototype log. The data dump itself stays out of git.

**Database setup:** point the prototype at a local restore of the snapshot. Use a role with `SELECT` only on the Cortico tables and write access only to a separate schema for the prototype-owned tables, so read-only is enforced by the database.

### Read-only, from Cortico

| V2 object | Used for | Key fields |
| --- | --- | --- |
| Conversation | Transcript list and switching | `id`, `title`, `start_time`, `forum_id`, `project_id`, `audio_url`, `language_codes` |
| Snippet | Transcript text, speakers, evidence anchors | `uuid`, `conversation_id`, `index_in_conversation`, `is_facilitator`, `speaker_name`, `content`, `words` (`word`, `start`, `end`, `confidence`) |
| Participant | Speaker attribution | `id`, `conversation_id`, `name`, `is_facilitator` |
| Conversation guide (sections, prompts) | The 5-6 guide questions users mark on a transcript | `sections[].prompts[].content`, `order` |
| Project, Forum, Community | Scoping the corpus | `id`, `name`, `organization_id` |

### Prototype-owned, V2-shaped

| Table | Mirrors | Purpose and key fields |
| --- | --- | --- |
| `research_question` | `Code` | `id`, `user_id`, `project_id`, `name`, `description`, `display_order`, `archived`, `created_at` |
| `highlight` | `Highlight`, `CreateHighlightSchema` | `id`, `user_id`, `conversation_id`, `project_id`, `title`, `content`, `notes` (the margin memo), `type`, `tool_id`, `metadata`, `starred` (prototype-owned flag), `created_at` |
| `highlight_snippet` | `CreateHighlightSnippetSchema` | `highlight_id`, `snippet_uuid`, `start_index`, `end_index` (word indices) |
| `voice_memo` | `Snippet.words` shape | `id`, `user_id`, `conversation_id`, `audio_path`, `duration`, `recorded_at`, `transcription_raw` (words JSON), `transcription_edited`, `transcription_engine`, `extracted_interests` (what the user wants to hear next), `status` |
| `reflection_connection` | `Coding` (`is_suggested`, `is_applied`, `ai_metadata`) | `id`, `voice_memo_id`, `research_question_id`, `insight_text`, `source` (`user`/`ai`), `status` (`suggested`/`accepted`/`edited`/`rejected`), `ai_metadata`, `created_at` |
| `connection_evidence` | `CreateHighlightSnippetSchema` | `id`, `connection_id`, `highlight_id` (nullable), `snippet_uuid`, `start_index`, `end_index`, `source` (`user`/`ai`) |
| `transcript_state` | none (UI state) | `user_id`, `conversation_id`, `reached_end_at`, `prompt_dismissed_at` |
| section\_checkpoint | none (user annotation; questions come from guide prompts) | id, user\_id, conversation\_id, snippet\_uuid, guide\_prompt\_id, created\_at |

The running RQ memo is a view over `reflection_connection` rows with status `accepted` or `edited`, joined to their evidence, voice memo, and conversation. It needs no table of its own.

### Gaps and decisions

- **Starring:** V2 can filter highlight shares by `starred` but exposes no way to set it, so starring is a prototype-owned flag on `highlight`.
- **Margin memos:** `Highlight.notes` holds one string, so one memo per highlight. If the recreated reader needs several memos per highlight, add a `highlight_memo` table.
- **Per-user RQs:** Cortico codebooks and codes are project-level with no owner, so RQs are prototype-owned. The shape stays close to `Code` to keep promotion straightforward.
- **Codings and shares:** V2 attaches codings to highlight shares, not highlights. Promotion into Cortico would need a share with `forum_id` and `project_id` per highlight; that is a promotion-time concern, not a prototype one.
- **IDs:** keep Cortico's integer IDs for referenced entities (`conversation_id`, `project_id`, `user_id`) and use the snippet `uuid` for passage anchors. Prototype tables use their own integer sequences.

* **Live memo:** filed entries can be edited and retracted. Add a `retracted` status to `reflection_connection`, an `updated_at` to it and to `connection_evidence`, and a `reflection_connection_revision` table (`id`, `connection_id`, `insight_text`, `evidence_snapshot`, `changed_at`) so prior versions are kept.

## Mock data shapes

Illustrative shapes for the main prototype-owned objects. Field names follow the data model section; the agent should adjust to `schema.sql`.

**Research question**

```json
{
  "id": 1,
  "user_id": 101,
  "project_id": 12,
  "name": "How do people describe trust in local institutions?",
  "description": "Look for stories where trust is built or broken.",
  "display_order": 0,
  "archived": false
}
```

**Highlight with margin memo and star**

```json
{
  "id": 5001,
  "user_id": 101,
  "conversation_id": 3302,
  "title": null,
  "notes": "Feels like a turning point for how she talks about the clinic.",
  "starred": true,
  "snippets": [
    { "uuid": "52b9e7e7-b7d5-42c2-9ed8-7293df3661fb", "word_indices": { "start_index": 2, "end_index": 10 } }
  ]
}
```

**Voice memo**

```json
{
  "id": 77,
  "user_id": 101,
  "conversation_id": 3302,
  "audio_path": "db/local/audio/voice_memo_77.webm",
  "duration": 142.6,
  "transcription_engine": "whisper (local)",
  "transcription_raw": [["I", 0.0, 0.2, 0.98], ["think", 0.2, 0.5, 0.97]],
  "transcription_edited": "I think I learned that trust here is about being known by name.",
  "extracted_interests": ["Hear from people who had the opposite experience with the clinic"],
  "status": "filed"
}
```

**AI-proposed connection with evidence**

```json
{
  "id": 410,
  "voice_memo_id": 77,
  "research_question_id": 1,
  "insight_text": "Trust seems to come from being recognized by name rather than from formal services.",
  "source": "ai",
  "status": "suggested",
  "ai_metadata": { "confidence": "medium", "rationale": "User mentioned being known by name; highlight 5001 is the closest passage." },
  "evidence": [
    { "highlight_id": 5001, "snippet_uuid": "52b9e7e7-b7d5-42c2-9ed8-7293df3661fb", "start_index": 2, "end_index": 10, "source": "user" },
    { "highlight_id": null, "snippet_uuid": "cc94e26e-9991-4f81-8f69-8e81eac8dd9f", "start_index": 0, "end_index": 5, "source": "ai" }
  ]
}
```

**Memo entry as rendered on the memo page** (assembled from the view, not stored)

```json
{
  "research_question_id": 1,
  "entries": [
    {
      "connection_id": 410,
      "insight_text": "Trust seems to come from being recognized by name rather than from formal services.",
      "conversation_id": 3302,
      "conversation_title": "Neighbors on the clinic",
      "voice_memo_id": 77,
      "filed_at": "2026-10-05T15:20:00Z",
      "evidence": [
        { "snippet_uuid": "52b9e7e7-b7d5-42c2-9ed8-7293df3661fb", "source": "user", "starred": true },
        { "snippet_uuid": "cc94e26e-9991-4f81-8f69-8e81eac8dd9f", "source": "ai", "starred": false }
      ]
    }
  ]
}
```

## Acceptance criteria

The prototype is ready for a test round when all of these hold.

**Reader and RQs**

- [ ] The recreated reader supports highlighting, margin memos, hover section navigation, and transcript switching.
- [ ] A highlight can be starred and unstarred, and the state persists after reload.
- [ ] RQs load from the config file on first run and can be edited, added, reordered, and archived from the side panel while reading.

* [ ] The user can drop a checkpoint on any speaker turn, assign it one of the guide's questions, and the hover menu updates to match.
* [ ] Checkpoints can be moved or deleted, persist after reload, and unmarked questions still show in the menu.

**Reflection**

- [ ] Reaching the end of a transcript shows the reflection prompt once; dismissing it loses no data. Trying to open another transcript without a recorded reflection shows a confirmation dialog with "Reflect now" and "Leave anyway" actions.
- [ ] The docked reflection panel shows the RQs, the four AI reflection questions, this transcript's highlights and memos (starred first), and a scrollable transcript at the same time.
- [ ] Recording can be started, paused, stopped, and redone; the audio file is saved and linked to the voice memo.
- [ ] Whisper returns a timestamped transcription in the `[word, start, end, confidence]` shape, stored alongside the user's edited text.

* [ ] Recording stops automatically at 20 minutes.

- [ ] A second voice memo can be recorded for the same transcript, and its entries appear after the first memo's entries in the memo.

**Review and filing**

- [x] The review step shows the transcription next to proposed RQ connections, each with evidence passages badged `yours` or `AI-suggested`. *Verified 2026-10-14: AI evidence that overlaps any of the user's highlights (starred or not) is linked via `highlight_id` and badged `yours`; review adds/edits and memo edits link the same way (`tests/test_evidence_provenance.py`). Existing dev-db rows need the additive backfill script (prototype log).*
- [x] Starred highlights always appear among candidate evidence; the user's other highlights are preferred over unhighlighted text. *Verified 2026-10-14: after the model returns, every starred highlight is either cited by an RQ connection or returned as starred-unassigned, whatever the model did. Evidence is ordered starred → other highlights → AI-only text (`tests/test_evidence_provenance.py`).*
- [ ] Each connection can be accepted, edited, or rejected, and the user can add one the AI missed.
- [ ] Nothing reaches the memo before "File to memo"; rejected proposals stay in the log with status `rejected`.
- [ ] A reflection that fits no RQ is shown as unmapped, not forced into one.

* [x] A starred highlight the voice memo never mentions is offered in review for RQ assignment; if left unassigned, it appears under "Starred, unassigned" on the memo page. *Verified 2026-10-14: review has an "Assign to: RQ" control per highlight, filed as a connection with that highlight as evidence. Highlights the AI cited no longer show as unassigned (`tests/test_evidence_provenance.py`). UI type-checked, not yet clicked through in a browser.*

- [ ] AI review calls use `gpt-5.6-luna` at `low` reasoning effort, set in config.
- [ ] The review prompt can be viewed, edited, saved, and reset to default from the UI, and the next review uses the saved version.

**Memo**

- [x] The full memo page shows one section per RQ with entries that link back to transcript passages and to the voice recording. *Verified 2026-10-14: evidence links go to `/?conversation=N&snippet=ID`, and the reader scrolls to and outlines that snippet. Type-checked, not yet clicked through in a browser.*
- [ ] The side-panel memo shows the same entries, compactly, while reading another transcript.

* [ ] A filed entry can be edited (insight text and evidence) and retracted from the memo page, and prior versions are kept.

**Data**

- [ ] The prototype's database role cannot write to any Cortico table.
- [ ] All new tables follow the data model section, and any deviation from `schema.sql` is noted in the prototype log.
- [ ] Audio and data dumps are gitignored.

## Open questions

- [ ] **Dismissed prompt:** decided that leaving a transcript without a recorded reflection triggers a confirmation dialog (see End-of-transcript prompt). Still open: should the dialog also appear when the user leaves before reaching the end of the transcript?
- [ ] **Facilitator-question sections:** decided for now: users mark sections manually with checkpoints. Still open: V2 conversation guides belong to a project and a conversation has no guide ID, so which guide version applies to a transcript? Assumed: the project's latest published version.
- [ ] **Memo editing after filing:** decided: the memo is a live doc, so filed entries stay editable and can be retracted. The data model supports it through `status`, and the edit controls are described under Memo page and side-panel memo.
- [ ] **Multiple reflections per transcript:** decided: a user can record more than one voice memo for the same transcript, and later ones are appended after earlier ones in recording order.
- [ ] **Recording length:** decided: 20 minutes is the maximum voice memo length for transcription speed and cost.
- [ ] **Which model reviews the memo:** decided: GPT-5.6 Luna at low reasoning effort, with a prompt the user can edit. Still open: how its outputs are validated against the transcript.
- [ ] **Starred highlights without a reflection:** decided: starred highlights that the voice memo never mentions still get filed as evidence. In review they are offered for assignment to an RQ; any left unassigned are listed as starred and unassigned on the memo page.
- [ ] **Consent for real users:** what consent and retention flow is needed before community members, not just the author, record voice memos?

## Follow-up work

Not built in this round, but the data model leaves room for each.

1. **Next-direction suggestions.** The AI reviews what the user said they want to hear next (stored as `extracted_interests`) and suggests directions or questions they may not have raised.
2. **Pointing to other parts of the corpus.** Using a topic mapping of the corpus, point the user to where the same topic, type of character, or type of narrative appears elsewhere. The retrieval approach is undecided: a topic-mapping tool such as Jev, a RAG system, or a hybrid.
3. **Convergence and divergence of memos.** Show how different people's memos and the AI's memo on the same transcript agree or differ. This needs multi-user support and a comparison view over `reflection_connection` and `connection_evidence`.
4. **Promotion into Cortico.** Map prototype-owned rows to V2 objects (highlights, highlight shares, codings) once write access is in scope.
5. **Consent, retention, and deletion** for voice recordings before wider testing.
