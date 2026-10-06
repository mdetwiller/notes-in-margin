import type { GuideQuestion } from "../lib/types";

interface Props {
  guideQuestions: GuideQuestion[];
  armedQuestionId: number | null;
  onArm: (guideQuestionId: number | null) => void;
  onJump: (snippetId: number) => void;
  onDelete: (guideQuestionId: number) => void;
}

export default function HoverSectionMenu({ guideQuestions, armedQuestionId, onArm, onJump, onDelete }: Props) {
  if (guideQuestions.length === 0) {
    return (
      <div className="hover-menu">
        <div className="hover-menu-panel">
          <p style={{ color: "#999" }}>No conversation guide found for this transcript.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="hover-menu">
      <div className="hover-menu-panel">
        <p style={{ fontWeight: "bold", marginBottom: "0.5rem" }}>Sections</p>
        {guideQuestions.map((q) => {
          const marked = q.checkpoint_snippet_id !== null;
          return (
            <div key={q.guide_question_id} style={{ marginBottom: "0.4rem" }}>
              <button
                className={marked ? "marked" : "unmarked"}
                onClick={() => (marked ? onJump(q.checkpoint_snippet_id!) : onArm(q.guide_question_id))}
              >
                {q.shorthand_code ?? q.text.slice(0, 40)}
                {!marked && armedQuestionId !== q.guide_question_id ? " (click a turn to mark)" : ""}
              </button>
              {marked && (
                <button
                  style={{ fontSize: "0.7rem", color: "#999" }}
                  onClick={() => onDelete(q.guide_question_id)}
                >
                  remove checkpoint
                </button>
              )}
              {!marked && armedQuestionId === q.guide_question_id && (
                <p style={{ color: "#8a5a00", fontSize: "0.75rem", margin: "0.2rem 0" }}>
                  Armed — click "Mark section start here" on a speaker turn in the transcript.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
