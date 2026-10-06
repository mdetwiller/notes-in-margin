interface Props {
  onReflect: () => void;
  onDismiss: () => void;
}

export default function EndOfTranscriptPrompt({ onReflect, onDismiss }: Props) {
  return (
    <div className="end-of-transcript-card">
      <span>You've reached the end of this conversation. Want to reflect on it?</span>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button className="primary" onClick={onReflect}>
          Reflect on this conversation
        </button>
        <button className="secondary" onClick={onDismiss}>
          Not now
        </button>
      </div>
    </div>
  );
}
