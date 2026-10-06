import { useState } from "react";
import { Link } from "react-router-dom";
import type { MemoResponse, ResearchQuestion } from "../lib/types";

interface Props {
  researchQuestions: ResearchQuestion[];
  onCreate: (name: string, description: string) => void;
  onUpdate: (id: number, body: { name?: string; description?: string; archived?: boolean }) => void;
  onReorder: (orderedIds: number[]) => void;
  memo: MemoResponse | null;
}

function RQTab({ researchQuestions, onCreate, onUpdate, onReorder }: Omit<Props, "memo">) {
  const [newName, setNewName] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const visible = researchQuestions.filter((rq) => showArchived || !rq.archived);

  function move(index: number, dir: -1 | 1) {
    const ids = visible.map((rq) => rq.id);
    const target = index + dir;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    onReorder(ids);
  }

  return (
    <div>
      {visible.map((rq, i) => (
        <div key={rq.id} className={"rq-item" + (rq.archived ? " archived" : "")}>
          <input
            defaultValue={rq.name}
            onBlur={(e) => e.target.value !== rq.name && onUpdate(rq.id, { name: e.target.value })}
          />
          <textarea
            defaultValue={rq.description ?? ""}
            rows={2}
            onBlur={(e) => e.target.value !== (rq.description ?? "") && onUpdate(rq.id, { description: e.target.value })}
          />
          <div style={{ display: "flex", gap: "0.3rem", marginTop: "0.3rem" }}>
            <button onClick={() => move(i, -1)}>&uarr;</button>
            <button onClick={() => move(i, 1)}>&darr;</button>
            <button onClick={() => onUpdate(rq.id, { archived: !rq.archived })}>
              {rq.archived ? "unarchive" : "archive"}
            </button>
          </div>
        </div>
      ))}
      <div style={{ marginTop: "0.75rem" }}>
        <input placeholder="New research question" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button
          className="secondary"
          style={{ marginTop: "0.3rem" }}
          onClick={() => {
            if (!newName.trim()) return;
            onCreate(newName, "");
            setNewName("");
          }}
        >
          Add RQ
        </button>
      </div>
      <label style={{ display: "block", marginTop: "1rem", fontSize: "0.8rem" }}>
        <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> show
        archived
      </label>
    </div>
  );
}

function MemoTab({ memo }: { memo: MemoResponse | null }) {
  if (!memo) return <p>Loading…</p>;
  return (
    <div>
      {memo.sections.map((section) => (
        <div key={section.research_question_id} style={{ marginBottom: "1rem" }}>
          <p style={{ fontWeight: "bold", marginBottom: "0.3rem" }}>{section.name}</p>
          {section.entries.length === 0 && <p style={{ color: "#999", fontSize: "0.8rem" }}>No entries yet.</p>}
          {section.entries.map((e) => (
            <div key={e.connection_id} style={{ fontSize: "0.85rem", marginBottom: "0.4rem" }}>
              <Link to="/memo">{e.insight_text}</Link>
              <div style={{ color: "#888", fontSize: "0.75rem" }}>{e.conversation_title}</div>
            </div>
          ))}
        </div>
      ))}
      <Link to="/memo">Open full memo →</Link>
    </div>
  );
}

export default function SidePanel(props: Props) {
  const [tab, setTab] = useState<"rq" | "memo">("rq");
  return (
    <div className="side-panel">
      <div className="side-panel-tabs">
        <button className={tab === "rq" ? "active" : ""} onClick={() => setTab("rq")}>
          RQs
        </button>
        <button className={tab === "memo" ? "active" : ""} onClick={() => setTab("memo")}>
          Memo
        </button>
      </div>
      <div className="side-panel-body">
        {tab === "rq" ? (
          <RQTab
            researchQuestions={props.researchQuestions}
            onCreate={props.onCreate}
            onUpdate={props.onUpdate}
            onReorder={props.onReorder}
          />
        ) : (
          <MemoTab memo={props.memo} />
        )}
      </div>
    </div>
  );
}
