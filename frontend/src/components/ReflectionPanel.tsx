import { useEffect, useRef, useState } from "react";
import type { ConversationDetail, Highlight, ResearchQuestion, VoiceMemo } from "../lib/types";
import { api } from "../lib/api";

const AI_REFLECTION_QUESTIONS = [
  "What do I think I learned?",
  "How do I know? Which examples in the conversation do I point to?",
  "What surprised me?",
  "What would be interesting or helpful to hear next?",
];

interface Props {
  conversation: ConversationDetail;
  researchQuestions: ResearchQuestion[];
  highlights: Highlight[];
  maxDurationSeconds: number;
  onJumpToHighlight: (snippetId: number) => void;
  onRecorded: (vm: VoiceMemo) => void;
  onClose: () => void;
}

type RecorderState = "idle" | "recording" | "paused" | "stopped" | "uploading" | "transcribing";

const POLL_INTERVAL_MS = 700;

function formatTime(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function ReflectionPanel({
  conversation,
  researchQuestions,
  highlights,
  maxDurationSeconds,
  onJumpToHighlight,
  onRecorded,
  onClose,
}: Props) {
  const [state, setState] = useState<RecorderState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0); // 0..1, for the live input meter

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const blobRef = useRef<Blob | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const meterFrameRef = useRef<number | null>(null);

  function stopMeter() {
    if (meterFrameRef.current !== null) cancelAnimationFrame(meterFrameRef.current);
    meterFrameRef.current = null;
    audioContextRef.current?.close().catch(() => {});
    audioContextRef.current = null;
    analyserRef.current = null;
    setAudioLevel(0);
  }

  function resumeMeterLoop() {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (const v of data) {
        const centered = (v - 128) / 128;
        sumSquares += centered * centered;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      setAudioLevel(Math.min(rms * 3.5, 1)); // scaled up — typical speech RMS is quiet
      meterFrameRef.current = requestAnimationFrame(tick);
    };
    tick();
  }

  function startMeter(stream: MediaStream) {
    const AudioContextClass = window.AudioContext ?? (window as any).webkitAudioContext;
    const audioContext = new AudioContextClass();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser); // analysis only — not connected to destination, so no echo
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    resumeMeterLoop();
  }

  useEffect(() => {
    return () => {
      timerRef.current && clearInterval(timerRef.current);
      pollRef.current && clearInterval(pollRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      stopMeter();
    };
  }, []);

  function startTimer() {
    timerRef.current && clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsed((prev) => {
        const next = prev + 1;
        if (next >= maxDurationSeconds) {
          stop();
        }
        return next;
      });
    }, 1000);
  }

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      recorder.start();
      mediaRecorderRef.current = recorder;
      setElapsed(0);
      setState("recording");
      startTimer();
      startMeter(stream);
    } catch {
      setError("Couldn't access the microphone. Check your browser's permission settings.");
    }
  }

  function pause() {
    mediaRecorderRef.current?.pause();
    timerRef.current && clearInterval(timerRef.current);
    if (meterFrameRef.current !== null) cancelAnimationFrame(meterFrameRef.current);
    meterFrameRef.current = null;
    setAudioLevel(0);
    setState("paused");
  }

  function resume() {
    mediaRecorderRef.current?.resume();
    startTimer();
    resumeMeterLoop();
    setState("recording");
  }

  function stop() {
    timerRef.current && clearInterval(timerRef.current);
    stopMeter();
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    recorder.onstop = () => {
      blobRef.current = new Blob(chunksRef.current, { type: "audio/webm" });
      streamRef.current?.getTracks().forEach((t) => t.stop());
      setState("stopped");
    };
    recorder.stop();
  }

  function reRecord() {
    blobRef.current = null;
    setElapsed(0);
    setState("idle");
  }

  async function saveAndTranscribe() {
    if (!blobRef.current) return;
    setState("uploading");
    setError(null);
    try {
      const vm = await api.uploadVoiceMemo(conversation.id, blobRef.current, elapsed);
      // The recording is saved as soon as this call returns (status "transcribing") —
      // transcription itself runs in the background, so poll for progress rather than
      // blocking on one long request.
      setState("transcribing");
      setTranscribeProgress(vm.transcription_progress);
      pollRef.current = setInterval(async () => {
        const latest = await api.getVoiceMemo(vm.id);
        setTranscribeProgress(latest.transcription_progress);
        if (latest.status === "ready_for_review") {
          pollRef.current && clearInterval(pollRef.current);
          onRecorded(latest);
        } else if (latest.status === "failed") {
          pollRef.current && clearInterval(pollRef.current);
          setError(
            `Transcription failed: ${latest.transcription_error ?? "unknown error"}. The recording is saved — you can try re-recording.`
          );
          setState("stopped");
        }
      }, POLL_INTERVAL_MS);
    } catch {
      setError("Saving the recording failed. You can try again.");
      setState("stopped");
    }
  }

  const sortedHighlights = [...highlights].sort((a, b) => Number(b.starred) - Number(a.starred));

  return (
    <div className="reflection-panel">
      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.75rem 1rem", borderBottom: "1px solid #eee" }}>
        <strong>Reflect on this conversation</strong>
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="body">
        <p style={{ fontSize: "0.8rem", color: "#888", margin: "0 0 1rem 0" }}>
          Scroll the transcript behind this panel while you record.
        </p>
        <section>
          <h4>Your research questions</h4>
          <ul>
            {researchQuestions.map((rq) => (
              <li key={rq.id}>{rq.name}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4>Reflection prompts</h4>
          <ul>
            {AI_REFLECTION_QUESTIONS.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4>Your highlights &amp; memos (starred first)</h4>
          {sortedHighlights.length === 0 && <p style={{ color: "#999", fontSize: "0.85rem" }}>None yet.</p>}
          {sortedHighlights.map((h) => (
            <div
              key={h.id}
              style={{ fontSize: "0.85rem", marginBottom: "0.4rem", cursor: "pointer" }}
              onClick={() => h.snippets[0] && onJumpToHighlight(h.snippets[0].snippet_id)}
            >
              {h.starred ? "★ " : ""}
              {h.notes || "(no memo text)"}
            </div>
          ))}
        </section>
        {error && <p style={{ color: "#b00" }}>{error}</p>}
      </div>
      {(state === "recording" || state === "paused") && (
        <div className="audio-meter-row">
          <div className="audio-meter">
            <div className="audio-meter-fill" style={{ width: `${Math.round(audioLevel * 100)}%` }} />
          </div>
          <span style={{ fontSize: "0.7rem", color: "#999" }}>
            {state === "paused" ? "paused" : audioLevel > 0.04 ? "picking up your voice" : "quiet — check your mic"}
          </span>
        </div>
      )}
      <div className="recorder-controls">
        {state === "idle" && <button className="primary" onClick={start}>Record</button>}
        {state === "recording" && (
          <>
            <button className="secondary" onClick={pause}>Pause</button>
            <button className="secondary" onClick={stop}>Stop</button>
          </>
        )}
        {state === "paused" && (
          <>
            <button className="secondary" onClick={resume}>Resume</button>
            <button className="secondary" onClick={stop}>Stop</button>
          </>
        )}
        {state === "stopped" && (
          <>
            <button className="secondary" onClick={reRecord}>Re-record</button>
            <button className="primary" onClick={saveAndTranscribe}>Save &amp; transcribe</button>
          </>
        )}
        {state === "uploading" && <span>Saving recording…</span>}
        {state === "transcribing" && <span>Transcribing… {Math.round(transcribeProgress * 100)}%</span>}
        <span className="recorder-timer">
          {formatTime(elapsed)} / {formatTime(maxDurationSeconds)}
        </span>
      </div>
    </div>
  );
}
