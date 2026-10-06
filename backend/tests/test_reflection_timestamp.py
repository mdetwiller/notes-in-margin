import json

from app.services.ai_review import reflection_timestamp_from_words

WORDS = json.dumps(
    [
        {"word": "I", "start": 0.0, "end": 0.2, "confidence": 0.9},
        {"word": "think", "start": 0.2, "end": 0.5, "confidence": 0.9},
        {"word": "trust", "start": 0.5, "end": 0.9, "confidence": 0.9},
    ]
)


def test_resolves_the_start_time_of_the_given_word():
    assert reflection_timestamp_from_words(WORDS, 2) == 0.5


def test_none_when_no_start_word_given():
    assert reflection_timestamp_from_words(WORDS, None) is None


def test_none_when_transcription_missing():
    assert reflection_timestamp_from_words(None, 0) is None


def test_none_when_index_out_of_range():
    assert reflection_timestamp_from_words(WORDS, 99) is None
    assert reflection_timestamp_from_words(WORDS, -1) is None
