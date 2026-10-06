import { useRef, useState } from "react";
import type { ConversationDetail, Highlight, HighlightSnippetSpan } from "../lib/types";

interface Selection_ {
  spans: HighlightSnippetSpan[];
  x: number;
  y: number;
}

interface Props {
  conversation: ConversationDetail;
  highlights: Highlight[];
  onCreateHighlight: (spans: HighlightSnippetSpan[], notes: string) => void;
  onToggleStar: (highlightId: number, starred: boolean) => void;
  armedCheckpointQuestionId: number | null;
  onDropCheckpoint: (snippetId: number) => void;
  activeWord: { snippetId: number; wordIndex: number } | null;
  onContainerScroll: (el: HTMLDivElement) => void;
}

function highlightForWord(highlights: Highlight[], snippetId: number, wordIndex: number): Highlight | null {
  for (const h of highlights) {
    for (const s of h.snippets) {
      if (s.snippet_id === snippetId && wordIndex >= s.start_index && wordIndex < s.end_index) return h;
    }
  }
  return null;
}

/** A highlight can span several speaker turns; show its margin memo once, under the last
 * (highest order_index) turn it touches, rather than repeating it under every turn. */
function lastSnippetIdForHighlight(h: Highlight, orderIndexBySnippetId: Map<number, number>): number {
  return h.snippets.reduce((lastId, s) => {
    const a = orderIndexBySnippetId.get(s.snippet_id) ?? -1;
    const b = orderIndexBySnippetId.get(lastId) ?? -1;
    return a > b ? s.snippet_id : lastId;
  }, h.snippets[0]?.snippet_id);
}

export default function TranscriptView({
  conversation,
  highlights,
  onCreateHighlight,
  onToggleStar,
  armedCheckpointQuestionId,
  onDropCheckpoint,
  activeWord,
  onContainerScroll,
}: Props) {
  const [selection, setSelection] = useState<Selection_ | null>(null);
  const [memoDraft, setMemoDraft] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const orderIndexBySnippetId = new Map(conversation.snippets.map((s) => [s.snippet_id, s.order_index]));
  const wordCountBySnippetId = new Map(conversation.snippets.map((s) => [s.snippet_id, s.words.length]));

  function handleMouseUp() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0 || !containerRef.current) return;
    const range = sel.getRangeAt(0);
    const startEl = (range.startContainer.parentElement as HTMLElement)?.closest("[data-widx]");
    const endEl = (range.endContainer.parentElement as HTMLElement)?.closest("[data-widx]");
    if (!startEl || !endEl) return;
    const startSnippetEl = startEl.closest("[data-snippet-id]") as HTMLElement | null;
    const endSnippetEl = endEl.closest("[data-snippet-id]") as HTMLElement | null;
    if (!startSnippetEl || !endSnippetEl) return;

    // A highlight can cross speaker turns — walk every snippet in document order between
    // the selection's two ends (selection may run backwards) and build one span per turn.
    const allSnippetEls = Array.from(containerRef.current.querySelectorAll("[data-snippet-id]"));
    const startPos = allSnippetEls.indexOf(startSnippetEl);
    const endPos = allSnippetEls.indexOf(endSnippetEl);
    const forward = startPos <= endPos;
    const [loPos, hiPos] = forward ? [startPos, endPos] : [endPos, startPos];
    const spanEls = allSnippetEls.slice(loPos, hiPos + 1) as HTMLElement[];

    const startWordIdx = parseInt(startEl.getAttribute("data-widx")!, 10);
    const endWordIdx = parseInt(endEl.getAttribute("data-widx")!, 10);
    const firstWordIdx = forward ? startWordIdx : endWordIdx;
    const lastWordIdx = forward ? endWordIdx : startWordIdx;

    const spans: HighlightSnippetSpan[] = spanEls.map((el, i) => {
      const snippetId = parseInt(el.getAttribute("data-snippet-id")!, 10);
      const isFirst = i === 0;
      const isLast = i === spanEls.length - 1;
      return {
        snippet_id: snippetId,
        start_index: isFirst ? firstWordIdx : 0,
        end_index: isLast ? lastWordIdx + 1 : (wordCountBySnippetId.get(snippetId) ?? lastWordIdx + 1),
      };
    });

    const rect = range.getBoundingClientRect();
    setSelection({ spans, x: rect.left, y: rect.bottom + window.scrollY });
    setMemoDraft("");
  }

  return (
    <div
      className="transcript-col"
      ref={containerRef}
      onScroll={(e) => onContainerScroll(e.currentTarget)}
      onMouseUp={handleMouseUp}
    >
      <div className="audio-bar">
        {conversation.has_audio ? (
          <span>Audio playback available</span>
        ) : (
          <span className="no-audio-note">No audio available for this conversation — showing transcript only.</span>
        )}
      </div>

      {conversation.snippets.map((s) => {
        const armed = armedCheckpointQuestionId !== null;
        return (
          <div className="snippet" key={s.snippet_id} data-snippet-id={s.snippet_id}>
            <div className="speaker-row" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className={"speaker" + (s.is_facilitator ? " facilitator" : "")}>
                {s.speaker_name ?? "Unknown speaker"}
              </span>
              {armed && (
                <button
                  className="secondary"
                  style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem" }}
                  onClick={() => onDropCheckpoint(s.snippet_id)}
                >
                  Mark section start here
                </button>
              )}
            </div>
            <p>
              {s.words.map((w, i) => {
                const highlight = highlightForWord(highlights, s.snippet_id, i);
                const isActive = activeWord?.snippetId === s.snippet_id && activeWord.wordIndex === i;
                const content = (
                  <span key={i} data-widx={i} className={isActive ? "word active" : "word"}>
                    {w.word}{" "}
                  </span>
                );
                if (!highlight) return content;
                return (
                  <mark
                    key={i}
                    className={"highlight" + (highlight.starred ? " starred" : "")}
                    title={highlight.notes ?? ""}
                    onClick={() => onToggleStar(highlight.id, !highlight.starred)}
                  >
                    {content}
                  </mark>
                );
              })}
            </p>
            {highlights
              .filter(
                (h) =>
                  h.notes &&
                  h.snippets.some((sp) => sp.snippet_id === s.snippet_id) &&
                  lastSnippetIdForHighlight(h, orderIndexBySnippetId) === s.snippet_id
              )
              .map((h) => (
                <div key={h.id} className="margin-memo">
                  {h.starred ? "★ " : ""}
                  {h.notes}
                </div>
              ))}
          </div>
        );
      })}

      {selection && (
        <div
          className="modal-backdrop"
          onClick={() => setSelection(null)}
          style={{ background: "transparent", alignItems: "flex-start", justifyContent: "flex-start" }}
        >
          <div
            className="modal"
            style={{ position: "absolute", left: selection.x, top: selection.y, maxWidth: 280 }}
            onClick={(e) => e.stopPropagation()}
          >
            <p style={{ margin: "0 0 0.5rem 0", fontFamily: "sans-serif", fontSize: "0.85rem" }}>
              Add a margin memo for this passage
            </p>
            <textarea
              autoFocus
              rows={3}
              style={{ width: "100%" }}
              value={memoDraft}
              onChange={(e) => setMemoDraft(e.target.value)}
              placeholder="Start typing to leave a memo..."
            />
            <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem" }}>
              <button
                className="primary"
                onClick={() => {
                  onCreateHighlight(selection.spans, memoDraft);
                  setSelection(null);
                }}
              >
                Save
              </button>
              <button className="secondary" onClick={() => setSelection(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
