"""Utilities for converting transcript data to various output formats."""

import webvtt

from reflector.db.transcripts import TranscriptParticipant, TranscriptTopic
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.processors.types import words_to_segments
from reflector.schemas.transcript_formats import TranscriptSegment
from reflector.utils.webvtt import _seconds_to_timestamp


def get_speaker_name(
    speaker: int, participants: list[TranscriptParticipant] | None
) -> str:
    """Get participant name for speaker or default to 'Speaker N'."""
    if participants:
        for participant in participants:
            if participant.speaker == speaker:
                return participant.name
    return f"Speaker {speaker}"


def format_timestamp_mmss(seconds: float) -> str:
    """Format seconds as MM:SS timestamp."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def transcript_to_text(
    topics: list[TranscriptTopic], participants: list[TranscriptParticipant] | None
) -> str:
    """Convert transcript topics to plain text with speaker names."""
    lines = []
    for topic in topics:
        if not topic.words:
            continue

        transcript = ProcessorTranscript(words=topic.words)
        segments = transcript.as_segments()

        for segment in segments:
            speaker_name = get_speaker_name(segment.speaker, participants)
            text = segment.text.strip()
            lines.append(f"{speaker_name}: {text}")

    return "\n".join(lines)


def transcript_to_text_timestamped(
    topics: list[TranscriptTopic], participants: list[TranscriptParticipant] | None
) -> str:
    """Convert transcript topics to timestamped text with speaker names."""
    lines = []
    for topic in topics:
        if not topic.words:
            continue

        transcript = ProcessorTranscript(words=topic.words)
        segments = transcript.as_segments()

        for segment in segments:
            speaker_name = get_speaker_name(segment.speaker, participants)
            timestamp = format_timestamp_mmss(segment.start)
            text = segment.text.strip()
            lines.append(f"[{timestamp}] {speaker_name}: {text}")

    return "\n".join(lines)


def topics_to_webvtt_named(
    topics: list[TranscriptTopic], participants: list[TranscriptParticipant] | None
) -> str:
    """Convert transcript topics to WebVTT format with participant names."""
    vtt = webvtt.WebVTT()

    for topic in topics:
        if not topic.words:
            continue

        segments = words_to_segments(topic.words)

        for segment in segments:
            speaker_name = get_speaker_name(segment.speaker, participants)
            text = segment.text.strip()
            text = f"<v {speaker_name}>{text}"

            caption = webvtt.Caption(
                start=_seconds_to_timestamp(segment.start),
                end=_seconds_to_timestamp(segment.end),
                text=text,
            )
            vtt.captions.append(caption)

    return vtt.content


def transcript_to_json_segments(
    topics: list[TranscriptTopic], participants: list[TranscriptParticipant] | None
) -> list[TranscriptSegment]:
    """Convert transcript topics to a flat list of JSON segments."""
    segments = []

    for topic in topics:
        if not topic.words:
            continue

        transcript = ProcessorTranscript(words=topic.words)
        for segment in transcript.as_segments():
            speaker_name = get_speaker_name(segment.speaker, participants)
            segments.append(
                TranscriptSegment(
                    speaker=segment.speaker,
                    speaker_name=speaker_name,
                    text=segment.text.strip(),
                    start=segment.start,
                    end=segment.end,
                )
            )

    return segments
