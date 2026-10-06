import { useState } from "react";
import type {
  ConnectionEvidence,
  ReflectionConnection,
  ResearchQuestion,
  ReviewResult,
  VoiceMemo,
} from "../lib/types";

interface Decision {
  action: "accept" | "edit" | "reject";
  insight_text: string;
  research_question_id: number | null;
  evidence: ConnectionEvidence[];
}

interface Props {
  voiceMemo: VoiceMemo;
  review: ReviewResult;
  researchQuestions: ResearchQuestion[];
  onEditTranscription: (text: string) => void;
  onFile: (
    decisions: {
      connection_id: number | null;
      action: "accept" | "edit" | "reject";
      research_question_id?: number | null;
      insight_text?: string;
      evidence?: ConnectionEvidence[];
    }[]
  ) => void;
  onClose: () => void;
  error?: string | null;
}

export default function ReviewStep({
  voiceMemo,
  review,
  researchQuestions,
  onEditTranscription,
  onFile,
  onClose,
  error,
}: Props) {
  const [transcription, setTranscription] = useState(voiceMemo.transcription_edited ?? "");
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [newInsight, setNewInsight] = useState("");
  const [newRqId, setNewRqId] = useState<number | "">("");

  const activeConnections = review.connections.filter((c) => c.status === "suggested");

  function setDecision(c: ReflectionConnection, patch: Partial<Decision>) {
    setDecisions((prev) => ({
      ...prev,
      [c.id]: {
        action: prev[c.id]?.action ?? "accept",
        insight_text: prev[c.id]?.insight_text ?? c.insight_text,
        research_question_id: prev[c.id]?.research_question_id ?? c.research_question_id,
        evidence: prev[c.id]?.evidence ?? c.evidence,
        ...patch,
      },
    }));
  }

  function rqName(id: number | null) {
    if (id === null) return "Unmapped — doesn't clearly connect to any RQ";
    return researchQuestions.find((rq) => rq.id === id)?.name ?? `RQ #${id}`;
  }

  function submitFile() {
    const fileDecisions = Object.entries(decisions).map(([connId, d]) => ({
      connection_id: Number(connId),
      action: d.action,
      research_question_id: d.research_question_id,
      insight_text: d.insight_text,
      evidence: d.evidence,
    }));
    if (newInsight.trim()) {
      fileDecisions.push({
        connection_id: null as unknown as number,
        action: "accept",
        research_question_id: newRqId === "" ? null : newRqId,
        insight_text: newInsight,
        evidence: [],
      });
    }
    onFile(
      fileDecisions.map((d) => ({
        ...d,
        connection_id: Number.isNaN(d.connection_id) ? null : (d.connection_id as number | null),
      }))
    );
  }

  return (
    <div className="modal-backdrop">
      <div className="modal wide">
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h3>Review reflection</h3>
          <button className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
        {error && (
          <p style={{ background: "#fff3e0", border: "1px solid #e0b84a", borderRadius: 6, padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}>
            {error}
          </p>
        )}
        <div className="review-columns">
          <div>
            <h4>Your transcription</h4>
            <textarea
              rows={16}
              style={{ width: "100%" }}
              value={transcription}
              onChange={(e) => setTranscription(e.target.value)}
              onBlur={() => onEditTranscription(transcription)}
            />
          </div>
          <div>
            <h4>Proposed RQ connections</h4>
            {activeConnections.length === 0 && <p style={{ color: "#999" }}>No connections proposed.</p>}
            {activeConnections.map((c) => {
              const decision = decisions[c.id];
              return (
                <div key={c.id} className={"connection-card" + (decision?.action === "reject" ? " rejected" : "")}>
                  <div style={{ fontSize: "0.75rem", color: "#666" }}>{rqName(c.research_question_id)}</div>
                  <textarea
                    rows={2}
                    style={{ width: "100%", margin: "0.3rem 0" }}
                    defaultValue={c.insight_text}
                    onChange={(e) => setDecision(c, { insight_text: e.target.value, action: "edit" })}
                  />
                  <div>
                    {c.evidence.map((e, i) => (
                      <div key={i} style={{ marginBottom: "0.3rem" }}>
                        <span className={"badge " + (e.source === "user" ? "yours" : "ai")}>
                          {e.source === "user" ? "yours" : "AI-suggested"}
                        </span>
                        <span style={{ fontSize: "0.85rem", fontStyle: "italic" }}>
                          "{e.text || "(couldn't resolve this passage's text)"}"
                        </span>
                      </div>
                    ))}
                  </div>
                  {c.ai_metadata && (
                    <div style={{ fontSize: "0.7rem", color: "#999", marginTop: "0.3rem" }}>
                      confidence: {c.ai_metadata.confidence} — {c.ai_metadata.rationale}
                    </div>
                  )}
                  <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.3rem" }}>
                    <button
                      className={decision?.action === "accept" ? "primary" : "secondary"}
                      onClick={() => setDecision(c, { action: "accept" })}
                    >
                      Accept
                    </button>
                    <button
                      className={decision?.action === "edit" ? "primary" : "secondary"}
                      onClick={() => setDecision(c, { action: "edit" })}
                    >
                      Edit
                    </button>
                    <button
                      className={decision?.action === "reject" ? "primary" : "secondary"}
                      onClick={() => setDecision(c, { action: "reject" })}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}

            {review.starred_unassigned.length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <h4>Starred highlights needing an RQ</h4>
                {review.starred_unassigned.map((h) => (
                  <div key={h.highlight_id} style={{ fontSize: "0.85rem" }}>
                    ★ {h.notes || "(no memo text)"}
                  </div>
                ))}
                <p style={{ fontSize: "0.75rem", color: "#999" }}>
                  Left unassigned, these will appear under "Starred, unassigned" on the memo page.
                </p>
              </div>
            )}

            <div className="connection-card">
              <div style={{ fontSize: "0.75rem", color: "#666" }}>Add a connection the AI missed</div>
              <textarea
                rows={2}
                style={{ width: "100%", margin: "0.3rem 0" }}
                value={newInsight}
                onChange={(e) => setNewInsight(e.target.value)}
                placeholder="What did you learn?"
              />
              <select value={newRqId} onChange={(e) => setNewRqId(e.target.value === "" ? "" : Number(e.target.value))}>
                <option value="">Unmapped</option>
                {researchQuestions.map((rq) => (
                  <option key={rq.id} value={rq.id}>
                    {rq.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div style={{ marginTop: "1rem", textAlign: "right" }}>
          <button className="primary" onClick={submitFile}>
            File to memo
          </button>
        </div>
      </div>
    </div>
  );
}
