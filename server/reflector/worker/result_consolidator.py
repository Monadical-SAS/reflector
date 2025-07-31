"""
@vibe-generated
Consolidate fragmented processor results into clean, deduplicated output
Similar to how CLI handles the data
"""

from typing import Any, Dict, List, Set, Tuple

from reflector.logger import logger


def consolidate_results(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate fragmented results from multiple processors into clean output.

    This mimics the CLI behavior which returns consolidated results instead of fragments.
    """
    consolidated = []

    # Group events by processor type
    events_by_processor = {}
    for event in events:
        processor = event.get("processor", "Unknown")
        if processor not in events_by_processor:
            events_by_processor[processor] = []
        events_by_processor[processor].append(event)

    # Process each processor type
    for processor, processor_events in events_by_processor.items():
        if processor == "TranscriptLinerProcessor":
            # Consolidate all TranscriptLinerProcessor fragments into one
            consolidated_event = _consolidate_transcript_liner(processor_events)
            if consolidated_event:
                consolidated.append(consolidated_event)

        elif processor == "AudioTranscriptModalProcessor":
            # Consolidate all AudioTranscriptModalProcessor chunks into one
            consolidated_event = _consolidate_audio_transcript(processor_events)
            if consolidated_event:
                consolidated.append(consolidated_event)

        elif processor == "TranscriptTranslatorProcessor":
            # Consolidate translator events
            consolidated_event = _consolidate_translator(processor_events)
            if consolidated_event:
                consolidated.append(consolidated_event)

        elif processor == "AudioDiarizationModalProcessor":
            # Include diarization results as-is
            consolidated.extend(processor_events)

        elif processor in (
            "TranscriptFinalTitleProcessor",
            "TranscriptFinalSummaryProcessor",
            "TranscriptTopicDetectorProcessor",
        ):
            # These processors should only have one event each, include as-is
            consolidated.extend(processor_events)

        else:
            # Unknown processor, include as-is
            logger.warning(f"Unknown processor type: {processor}")
            consolidated.extend(processor_events)

    return consolidated


def _consolidate_transcript_liner(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate multiple TranscriptLinerProcessor events into one."""
    if not events:
        return None

    # Collect all words with deduplication by position
    all_words = []
    seen_positions: Set[Tuple[float, float]] = set()

    for event in events:
        data = event.get("data", {})
        words = data.get("words", [])

        for word in words:
            pos_key = (word.get("start", 0), word.get("end", 0))
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                all_words.append(word)

    # Sort words by start time
    all_words.sort(key=lambda w: w.get("start", 0))

    # Get translation from the last event (if any)
    translation = None
    for event in reversed(events):
        data = event.get("data", {})
        if data.get("translation"):
            translation = data["translation"]
            break

    # Create consolidated event
    return {
        "processor": "TranscriptLinerProcessor",
        "uid": events[0].get("uid", "consolidated"),
        "data": {"words": all_words, "translation": translation},
    }


def _consolidate_audio_transcript(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate multiple AudioTranscriptModalProcessor events into one."""
    if not events:
        return None

    # Collect all words with deduplication
    all_words = []
    seen_positions: Set[Tuple[float, float]] = set()

    for event in events:
        data = event.get("data", {})
        words = data.get("words", [])

        for word in words:
            pos_key = (word.get("start", 0), word.get("end", 0))
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                all_words.append(word)

    # Sort words by start time
    all_words.sort(key=lambda w: w.get("start", 0))

    return {
        "processor": "AudioTranscriptModalProcessor",
        "uid": events[0].get("uid", "consolidated"),
        "data": {
            "segments": None,
            "topics": None,
            "title": None,
            "summary": None,
            "words": all_words,
        },
    }


def _consolidate_translator(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate multiple TranscriptTranslatorProcessor events into one."""
    if not events:
        return None

    # Collect all words and translations
    all_words = []
    seen_positions: Set[Tuple[float, float]] = set()
    translations = []

    for event in events:
        data = event.get("data", {})
        words = data.get("words", [])

        for word in words:
            pos_key = (word.get("start", 0), word.get("end", 0))
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                all_words.append(word)

        if data.get("translation"):
            translation = data["translation"]
            # Handle both string and dict translations
            if isinstance(translation, dict):
                translations.append(translation.get("text", ""))
            else:
                translations.append(translation)

    # Sort words by start time
    all_words.sort(key=lambda w: w.get("start", 0))

    # Combine translations
    combined_translation = " ".join(translations) if translations else None

    # If we have the original translation dict structure, use it
    if (
        events
        and len(events) == 1
        and isinstance(events[0].get("data", {}).get("translation"), dict)
    ):
        # Return the original single event as-is for dict translations
        return events[0]

    # Otherwise, consolidate multiple string translations
    return {
        "processor": "TranscriptTranslatorProcessor",
        "uid": events[0].get("uid", "consolidated") if events else "consolidated",
        "data": {"words": all_words, "translation": combined_translation},
    }
