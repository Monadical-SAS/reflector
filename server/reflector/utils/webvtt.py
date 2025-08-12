"""WebVTT utilities for generating subtitle files from transcript data."""

from typing import TYPE_CHECKING

import webvtt

from reflector.processors.types import Seconds, Word, words_to_segments
from reflector.utils.webvtt_types import WebvttText, cast_webvtt

if TYPE_CHECKING:
    from reflector.db.transcripts import TranscriptTopic


def _seconds_to_timestamp(seconds: Seconds) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def words_to_webvtt(words: list[Word]) -> WebvttText:
    """Convert words to WebVTT using existing segmentation logic."""
    vtt = webvtt.WebVTT()
    if not words:
        return cast_webvtt(vtt.content)

    segments = words_to_segments(words)

    for segment in segments:
        text = segment.text.strip()
        text = f"<v Speaker{segment.speaker}>{text}"

        caption = webvtt.Caption(
            start=_seconds_to_timestamp(segment.start),
            end=_seconds_to_timestamp(segment.end),
            text=text,
        )
        vtt.captions.append(caption)

    return cast_webvtt(vtt.content)


def topics_to_webvtt(topics: list["TranscriptTopic"]) -> WebvttText:
    if not topics:
        return cast_webvtt(webvtt.WebVTT().content)

    all_words: list[Word] = []
    for topic in topics:
        all_words.extend(topic.words)

    # assert it's in sequence
    for i in range(len(all_words) - 1):
        assert (
            all_words[i].start <= all_words[i + 1].start
        ), f"Words are not in sequence: {all_words[i].text} and {all_words[i + 1].text} are not consecutive: {all_words[i].start} > {all_words[i + 1].start}"

    return words_to_webvtt(all_words)
