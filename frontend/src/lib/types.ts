export interface ConversationSummary {
  id: number;
  title: string;
  project_id: number;
  duration_seconds: number;
  language: string;
  audio_url: string | null;
  has_audio: boolean;
}

export interface Word {
  word: string;
  start: number;
  end: number;
  confidence: number;
}

export interface Snippet {
  snippet_id: number;
  order_index: number;
  speaker_name: string | null;
  is_facilitator: boolean;
  start_offset: number;
  end_offset: number;
  text: string;
  words: Word[];
}

export interface GuideQuestion {
  guide_question_id: number;
  text: string;
  shorthand_code: string | null;
  order_index: number;
  checkpoint_snippet_id: number | null;
}

export interface ConversationDetail {
  id: number;
  title: string;
  audio_url: string | null;
  has_audio: boolean;
  duration_seconds: number;
  language: string;
  snippets: Snippet[];
  guide_questions: GuideQuestion[];
  transcript_state: { reached_end_at: string | null; prompt_dismissed_at: string | null };
}

export interface HighlightSnippetSpan {
  snippet_id: number;
  start_index: number;
  end_index: number;
  text?: string;
}

export interface Highlight {
  id: number;
  conversation_id: number;
  title: string | null;
  notes: string | null;
  starred: boolean;
  created_at: string;
  snippets: HighlightSnippetSpan[];
}

export interface ResearchQuestion {
  id: number;
  name: string;
  description: string | null;
  display_order: number;
  archived: boolean;
}

export interface VoiceMemo {
  id: number;
  conversation_id: number;
  audio_path: string;
  duration: number;
  recorded_at: string;
  transcription_raw: string | null;
  transcription_edited: string | null;
  transcription_engine: string | null;
  transcription_progress: number;
  transcription_error: string | null;
  extracted_interests: string | null;
  status: "recorded" | "transcribing" | "ready_for_review" | "filed" | "failed";
}

export type EvidenceSource = "user" | "ai";

export interface ConnectionEvidence {
  id?: number;
  highlight_id: number | null;
  snippet_id: number;
  start_index: number;
  end_index: number;
  source: EvidenceSource;
  starred?: boolean;
  text?: string;
}

export interface ReflectionConnection {
  id: number;
  research_question_id: number | null;
  insight_text: string;
  source: "user" | "ai";
  status: "suggested" | "accepted" | "edited" | "rejected" | "retracted";
  edited_from_ai: boolean;
  ai_metadata: {
    model: string;
    reasoning_effort: string;
    confidence: string;
    rationale: string;
    reflection_timestamp: number | null;
  } | null;
  evidence: ConnectionEvidence[];
}

export interface StarredUnassignedHighlight {
  highlight_id: number;
  notes: string | null;
  snippets: HighlightSnippetSpan[];
}

export interface ReviewResult {
  connections: ReflectionConnection[];
  starred_unassigned: StarredUnassignedHighlight[];
}

export interface MemoEntry {
  connection_id: number;
  insight_text: string;
  source: "user" | "ai";
  edited_from_ai: boolean;
  conversation_id: number;
  conversation_title: string;
  voice_memo_id: number;
  voice_memo_audio_path: string | null;
  reflection_timestamp: number | null;
  filed_at: string;
  evidence: ConnectionEvidence[];
}

export interface MemoSection {
  research_question_id: number;
  name: string;
  archived: boolean;
  entries: MemoEntry[];
}

export interface MemoStarredUnassignedGroup {
  conversation_id: number;
  conversation_title: string;
  highlights: StarredUnassignedHighlight[];
}

export interface MemoResponse {
  sections: MemoSection[];
  unmapped: MemoEntry[];
  starred_unassigned: MemoStarredUnassignedGroup[];
}

export interface NextStepSuggestion {
  id: number;
  research_question_id: number | null;
  suggested_direction: string | null;
  recommended_conversation_id: number | null;
  recommended_conversation_title: string | null;
  rationale: string;
  status: "suggested" | "accepted" | "dismissed";
  ai_metadata: { model: string; reasoning_effort: string; prompt: string } | null;
  created_at: string;
}

export interface CodeFamilyMember {
  connection_id: number;
  insight_text: string;
}

export interface CodeFamily {
  id: number;
  research_question_id: number;
  name: string;
  definition: string;
  status: "suggested" | "accepted" | "dismissed" | "merged";
  members: CodeFamilyMember[];
  ai_metadata: { model: string; reasoning_effort: string; prompt: string } | null;
  created_at: string;
}

export interface CodeFamilyMergeSuggestion {
  id: number;
  research_question_id: number;
  family_ids: number[];
  target_family_id: number;
  proposed_name: string;
  proposed_definition: string;
  rationale: string | null;
  status: "suggested" | "accepted" | "dismissed";
  created_at: string;
}

export interface CodeFamilyState {
  families: CodeFamily[];
  merge_suggestions: CodeFamilyMergeSuggestion[];
  cap: { live_count: number; max_per_rq: number; near_cap: boolean; at_cap: boolean };
  withheld_new_families: number;
}
