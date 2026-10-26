import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type {
  ConversationDetail,
  ConversationSummary,
  Highlight,
  HighlightSnippetSpan,
  MemoResponse,
  ResearchQuestion,
  ReviewResult,
  VoiceMemo,
} from "../lib/types";
import TranscriptView from "../components/TranscriptView";
import HoverSectionMenu from "../components/HoverSectionMenu";
import SidePanel from "../components/SidePanel";
import EndOfTranscriptPrompt from "../components/EndOfTranscriptPrompt";
import LeaveConfirmationDialog from "../components/LeaveConfirmationDialog";
import ReflectionPanel from "../components/ReflectionPanel";
import ReviewStep from "../components/ReviewStep";

const MAX_VOICE_MEMO_SECONDS = 1200;

export default function ReaderPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [researchQuestions, setResearchQuestions] = useState<ResearchQuestion[]>([]);
  const [memo, setMemo] = useState<MemoResponse | null>(null);
  const [recordedVoiceMemoExists, setRecordedVoiceMemoExists] = useState(false);
  const [attentionVoiceMemos, setAttentionVoiceMemos] = useState<
    { vm: VoiceMemo; pendingCount: number }[]
  >([]);

  const [armedQuestionId, setArmedQuestionId] = useState<number | null>(null);
  const [showEndPrompt, setShowEndPrompt] = useState(false);
  const [showReflectionPanel, setShowReflectionPanel] = useState(false);
  const [activeVoiceMemo, setActiveVoiceMemo] = useState<VoiceMemo | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [pendingSwitchId, setPendingSwitchId] = useState<number | null>(null);
  const reachedEndRef = useRef(false);

  useEffect(() => {
    api.listConversations().then((cs) => {
      setConversations(cs);
      const requested = Number(new URLSearchParams(window.location.search).get("conversation"));
      const initial = cs.find((c) => c.id === requested)?.id ?? cs[0]?.id;
      if (initial !== undefined) setConversationId(initial);
    });
    api.listResearchQuestions().then(setResearchQuestions);
    refreshMemo();
  }, []);

  function refreshMemo() {
    api.getMemo().then(setMemo);
  }

  useEffect(() => {
    if (conversationId === null) return;
    reachedEndRef.current = false;
    setShowEndPrompt(false);
    setArmedQuestionId(null);
    api.getConversation(conversationId).then((c) => {
      setConversation(c);
      reachedEndRef.current = !!c.transcript_state.reached_end_at;
    });
    api.listHighlights(conversationId).then(setHighlights);
    refreshVoiceMemoStatus(conversationId);
  }, [conversationId]);

  async function refreshVoiceMemoStatus(id: number) {
    const vms = await api.listVoiceMemosForConversation(id);
    // Any recording counts as "reflected" for the leave dialog, even one not yet reviewed
    // or filed — the attention banner already covers finishing those.
    setRecordedVoiceMemoExists(vms.some((vm) => vm.status !== "failed"));

    // A reflection needs attention if it was never reviewed at all, or if it has any
    // connection still sitting as "suggested" — e.g. one the user never got to decide on
    // before clicking "File to memo" on the rest. That can happen even on an already-filed
    // memo, so this checks actual connection status, not just vm.status.
    const withPending = await Promise.all(
      vms
        .filter((vm) => vm.status === "ready_for_review" || vm.status === "filed")
        .map(async (vm) => {
          const review = await api.getReview(vm.id).catch(() => ({ connections: [], starred_unassigned: [] }));
          const pendingCount = review.connections.filter((c) => c.status === "suggested").length;
          // A ready_for_review memo with zero connections at all was never reviewed yet —
          // still needs attention even though nothing is technically "pending".
          const neverReviewed = vm.status === "ready_for_review" && review.connections.length === 0;
          return { vm, pendingCount, neverReviewed };
        })
    );
    const stillTranscribing = vms.filter((vm) => vm.status === "transcribing" || vm.status === "failed");

    setAttentionVoiceMemos([
      ...withPending
        .filter((w) => w.pendingCount > 0 || w.neverReviewed)
        .map(({ vm, pendingCount }) => ({ vm, pendingCount })),
      ...stillTranscribing.map((vm) => ({ vm, pendingCount: 0 })),
    ]);
  }

  function hasUnsavedReflectionRisk() {
    // Confirm leaving whenever the user has engaged with this transcript at all — reached
    // the end, highlighted, or dropped a checkpoint — not only once they've reached the
    // end. Merely opening a transcript and leaving doesn't count, so browsing the
    // conversation list doesn't nag.
    const engaged =
      reachedEndRef.current ||
      highlights.length > 0 ||
      !!conversation?.guide_questions.some((q) => q.checkpoint_snippet_id !== null);
    return engaged && !recordedVoiceMemoExists;
  }

  function requestSwitch(nextId: number) {
    if (nextId === conversationId) return;
    if (hasUnsavedReflectionRisk()) {
      setPendingSwitchId(nextId);
    } else {
      setConversationId(nextId);
    }
  }

  function handleContainerScroll(el: HTMLDivElement) {
    const nearEnd = el.scrollTop + el.clientHeight >= el.scrollHeight - 40;
    if (nearEnd && !reachedEndRef.current && conversationId !== null) {
      reachedEndRef.current = true;
      setShowEndPrompt(true);
      api.setTranscriptState(conversationId, { reached_end_at: true });
    }
  }

  function dismissEndPrompt() {
    setShowEndPrompt(false);
    if (conversationId !== null) api.setTranscriptState(conversationId, { prompt_dismissed: true });
  }

  async function handleCreateHighlight(spans: HighlightSnippetSpan[], notes: string) {
    if (conversationId === null) return;
    const h = await api.createHighlight(conversationId, { notes, snippets: spans });
    setHighlights((prev) => [...prev, h]);
  }

  async function handleToggleStar(highlightId: number, starred: boolean) {
    const updated = await api.updateHighlight(highlightId, { starred });
    setHighlights((prev) => prev.map((h) => (h.id === highlightId ? updated : h)));
  }

  async function handleDropCheckpoint(snippetId: number) {
    if (conversationId === null || armedQuestionId === null) return;
    await api.setCheckpoint(conversationId, armedQuestionId, snippetId);
    setArmedQuestionId(null);
    setConversation(await api.getConversation(conversationId));
  }

  async function handleDeleteCheckpoint(guideQuestionId: number) {
    if (conversationId === null) return;
    await api.deleteCheckpoint(conversationId, guideQuestionId);
    setConversation(await api.getConversation(conversationId));
  }

  function jumpToSnippet(snippetId: number) {
    document.querySelector(`[data-snippet-id="${snippetId}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // A memo evidence link (/?conversation=N&snippet=ID) lands on the cited passage, not the
  // top of the transcript. Once per page load, so later re-fetches don't yank the scroll.
  const linkedSnippetHandledRef = useRef(false);
  useEffect(() => {
    if (linkedSnippetHandledRef.current || !conversation) return;
    const params = new URLSearchParams(window.location.search);
    const snippetId = Number(params.get("snippet"));
    if (!snippetId || conversation.id !== Number(params.get("conversation"))) return;
    linkedSnippetHandledRef.current = true;
    requestAnimationFrame(() => {
      jumpToSnippet(snippetId);
      const el = document.querySelector<HTMLElement>(`[data-snippet-id="${snippetId}"]`);
      if (!el) return;
      el.style.outline = "2px solid #e0b84a";
      setTimeout(() => (el.style.outline = ""), 2500);
    });
  }, [conversation]);

  async function openReview(vm: VoiceMemo) {
    // The recording and transcription are already saved at this point. The AI review call
    // is a separate, best-effort step — if it fails (e.g. no OPENAI_API_KEY configured),
    // the user should still land on the review screen with their transcription intact and
    // be able to add connections by hand, rather than the panel just closing with no
    // visible result.
    setActiveVoiceMemo(vm);
    setShowReflectionPanel(false);
    setReviewError(null);
    try {
      const review = await api.runReview(vm.id);
      setReviewResult(review);
    } catch (e) {
      setReviewError(
        `AI review unavailable (${e instanceof Error ? e.message : "unknown error"}). Your recording and transcription are saved — you can still add connections by hand below.`
      );
      // Fall back to whatever's already on record (e.g. starred-unassigned highlights)
      // rather than a hard-coded empty result — the AI call failed, not everything else.
      const fallback = await api.getReview(vm.id).catch(() => ({ connections: [], starred_unassigned: [] }));
      setReviewResult(fallback);
    }
  }

  async function handleRecorded(vm: VoiceMemo) {
    setRecordedVoiceMemoExists(true);
    await openReview(vm);
  }

  async function resumeReview(vm: VoiceMemo) {
    // Resuming is distinct from a first-time review: it must never re-run the AI, which
    // would generate a fresh batch of suggestions alongside ones already accepted/rejected
    // instead of just showing what's still pending. Only fall through to a first-time
    // openReview() when nothing has ever been generated for this memo.
    setReviewError(null);
    const existing = await api.getReview(vm.id).catch(() => null);
    if (existing && existing.connections.length > 0) {
      setActiveVoiceMemo(vm);
      setShowReflectionPanel(false);
      setReviewResult(existing);
    } else {
      await openReview(vm);
    }
  }

  async function handleFileToMemo(
    decisions: Parameters<typeof api.fileToMemo>[1]
  ) {
    if (!activeVoiceMemo) return;
    await api.fileToMemo(activeVoiceMemo.id, decisions);
    setReviewResult(null);
    setActiveVoiceMemo(null);
    setReviewError(null);
    setRecordedVoiceMemoExists(true);
    refreshMemo();
    if (conversationId !== null) refreshVoiceMemoStatus(conversationId);
  }

  if (conversationId === null || !conversation) {
    return <p style={{ padding: "2rem" }}>Loading…</p>;
  }

  return (
    <>
      <div className="topnav" style={{ borderBottom: "none", paddingTop: 0 }}>
        <select value={conversationId} onChange={(e) => requestSwitch(Number(e.target.value))}>
          {conversations.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title} (#{c.id})
            </option>
          ))}
        </select>
        <button className="secondary" onClick={() => setShowReflectionPanel(true)}>
          Record a reflection
        </button>
      </div>
      {attentionVoiceMemos.length > 0 && (
        <div style={{ background: "#fff3e0", borderBottom: "1px solid #e0b84a", padding: "0.5rem 1.5rem", fontSize: "0.85rem", fontFamily: "sans-serif", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {attentionVoiceMemos.map(({ vm, pendingCount }) => (
            <span key={vm.id}>
              {(vm.status === "ready_for_review" || vm.status === "filed") && (
                <>
                  Reflection recorded {new Date(vm.recorded_at).toLocaleString()}
                  {pendingCount > 0
                    ? ` has ${pendingCount} connection${pendingCount > 1 ? "s" : ""} still undecided`
                    : " was never reviewed"}
                  .{" "}
                  <button className="secondary" style={{ padding: "0.1rem 0.5rem" }} onClick={() => resumeReview(vm)}>
                    Resume review
                  </button>
                </>
              )}
              {vm.status === "transcribing" && <>Still transcribing a reflection from {new Date(vm.recorded_at).toLocaleString()}…</>}
              {vm.status === "failed" && <>Transcription failed for a reflection recorded {new Date(vm.recorded_at).toLocaleString()} — the audio is saved, but you'll need to re-record to get a transcription.</>}
            </span>
          ))}
        </div>
      )}
      <div className="reader-layout">
        <HoverSectionMenu
          guideQuestions={conversation.guide_questions}
          armedQuestionId={armedQuestionId}
          onArm={setArmedQuestionId}
          onJump={jumpToSnippet}
          onDelete={handleDeleteCheckpoint}
        />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {showEndPrompt && (
            <div style={{ padding: "0 2rem" }}>
              <EndOfTranscriptPrompt onReflect={() => setShowReflectionPanel(true)} onDismiss={dismissEndPrompt} />
            </div>
          )}
          <TranscriptView
            conversation={conversation}
            highlights={highlights}
            onCreateHighlight={handleCreateHighlight}
            onToggleStar={handleToggleStar}
            armedCheckpointQuestionId={armedQuestionId}
            onDropCheckpoint={handleDropCheckpoint}
            activeWord={null}
            onContainerScroll={handleContainerScroll}
          />
        </div>
        <SidePanel
          researchQuestions={researchQuestions}
          onCreate={(name, description) => api.createResearchQuestion({ name, description }).then((rq) => setResearchQuestions((p) => [...p, rq]))}
          onUpdate={(id, body) => api.updateResearchQuestion(id, body).then((rq) => setResearchQuestions((p) => p.map((r) => (r.id === id ? rq : r))))}
          onReorder={(ids) => api.reorderResearchQuestions(ids).then(() => api.listResearchQuestions().then(setResearchQuestions))}
          memo={memo}
        />
      </div>

      {showReflectionPanel && (
        <ReflectionPanel
          conversation={conversation}
          researchQuestions={researchQuestions}
          highlights={highlights}
          maxDurationSeconds={MAX_VOICE_MEMO_SECONDS}
          onJumpToHighlight={jumpToSnippet}
          onRecorded={handleRecorded}
          onClose={() => setShowReflectionPanel(false)}
        />
      )}

      {activeVoiceMemo && !reviewResult && !reviewError && (
        <div className="reflection-panel" style={{ padding: "1.5rem", fontFamily: "sans-serif" }}>
          Reviewing your reflection against your research questions… this calls out to the AI
          and can take a few seconds.
        </div>
      )}

      {activeVoiceMemo && reviewResult && (
        <ReviewStep
          voiceMemo={activeVoiceMemo}
          review={reviewResult}
          researchQuestions={researchQuestions}
          error={reviewError}
          onEditTranscription={(text) => api.editVoiceMemoTranscription(activeVoiceMemo.id, text)}
          onFile={handleFileToMemo}
          onClose={() => {
            setReviewResult(null);
            setActiveVoiceMemo(null);
            setReviewError(null);
          }}
        />
      )}

      {pendingSwitchId !== null && (
        <LeaveConfirmationDialog
          onReflectNow={() => {
            setPendingSwitchId(null);
            setShowReflectionPanel(true);
          }}
          onLeaveAnyway={() => {
            setConversationId(pendingSwitchId);
            setPendingSwitchId(null);
          }}
        />
      )}
    </>
  );
}
