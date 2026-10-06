interface Props {
  onReflectNow: () => void;
  onLeaveAnyway: () => void;
}

export default function LeaveConfirmationDialog({ onReflectNow, onLeaveAnyway }: Props) {
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <p>Are you sure you want to leave this transcript without recording your reflections?</p>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
          <button className="primary" onClick={onReflectNow}>
            Reflect now
          </button>
          <button className="secondary" onClick={onLeaveAnyway}>
            Leave anyway
          </button>
        </div>
      </div>
    </div>
  );
}
