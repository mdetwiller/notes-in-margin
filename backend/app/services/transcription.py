"""Local Whisper transcription (faster-whisper), chosen over whisper.cpp for this
prototype since it's pip-installable with no separate compile step.

Interface contract per the PRD: audio in, timestamped text out, in the same
{word, start, end, confidence} shape as Cortico's snippet.words (see docs/prototype-log.md
for why this is a dict shape, not the PRD mock's [word, start, end, confidence] tuple).
"""
from __future__ import annotations

import json
from collections.abc import Callable
from functools import lru_cache

from ..config import Config

ENGINE_LABEL = "faster-whisper (local)"


@lru_cache
def _get_model(model_size: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device="cpu", compute_type=compute_type)


def transcribe(
    audio_path: str, config: Config, on_progress: Callable[[float], None] | None = None
) -> tuple[str, str]:
    """Returns (plain_text, words_json) where words_json matches snippet.words' shape:
    a JSON array of {"word", "start", "end", "confidence"} objects.

    faster-whisper yields segments lazily as it decodes, so progress is reported after
    each segment as (segment.end / total audio duration) — real coverage of the audio,
    not a fake spinner."""
    model = _get_model(config.transcription.model_size, config.transcription.compute_type)
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    total_duration = info.duration or 1.0

    words = []
    texts = []
    for segment in segments:
        texts.append(segment.text.strip())
        for word in segment.words or []:
            words.append(
                {
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    # faster-whisper exposes per-word probability, not a raw "confidence" —
                    # reused here as the closest equivalent to Cortico's word.confidence.
                    "confidence": round(word.probability, 5),
                }
            )
        if on_progress:
            on_progress(min(segment.end / total_duration, 1.0))

    if on_progress:
        on_progress(1.0)

    return " ".join(texts).strip(), json.dumps(words)
