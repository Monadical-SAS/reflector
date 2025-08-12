"""WebVTT type definitions with validation."""

import logging
from io import StringIO
from typing import Annotated, Any, Callable, Iterator, TypeAlias, cast

import webvtt
from pydantic import AfterValidator, Field

logger = logging.getLogger(__name__)


def _check_vtt_header(v: str) -> str:
    """Check for valid WebVTT header"""
    if not v.strip().startswith("WEBVTT"):
        raise ValueError("WebVTT content must start with 'WEBVTT'")
    return v


def _validate_webvtt(v: str) -> str:
    """Validate WebVTT format for pydantic AfterValidator.

    NOTE: We intentionally only check the header, not parse the full WebVTT.
    This is because:
    1. Full parsing is expensive for large transcripts
    2. We trust the data coming from our own processors
    3. The webvtt library will handle parsing when needed
    4. This provides a fast sanity check without performance overhead
    """
    if not v:
        # Allow empty strings for nullable fields per pydantic conventions
        return v

    # Only check header - this is intentional, see docstring
    _check_vtt_header(v)

    return v


# Branded type for WebVTT text
WebvttText: TypeAlias = Annotated[
    str,
    AfterValidator(_validate_webvtt),
    Field(description="Valid WebVTT formatted text"),
]


def cast_webvtt(content: str) -> WebvttText:
    """Cast a string to WebvttText when we know it's valid (e.g., from webvtt library)."""
    return cast(WebvttText, content)


def parse_webvtt_from_db(raw_content: str) -> WebvttText:
    """Parse WebVTT content from database, validating it.

    NOTE: Uses _check_vtt_header directly for consistency with _validate_webvtt.
    We only validate the header, not the full content (see _validate_webvtt docstring).
    """
    return cast(WebvttText, _check_vtt_header(raw_content))


class Webvtt:
    """
    A data structure wrapping a parsed WebVTT object.

    Provides idiomatic Python iteration and comprehension support for captions.
    """

    def __init__(self, webvtt_text: str | WebvttText):
        """Initialize from WebVTT text content."""
        if isinstance(webvtt_text, str):
            validated_text = _check_vtt_header(webvtt_text)
        else:
            validated_text = webvtt_text

        buffer = StringIO(validated_text)
        self._vtt = webvtt.read_buffer(buffer)

    @property
    def captions(self) -> list[webvtt.Caption]:
        """Get the list of captions."""
        return self._vtt.captions

    def __iter__(self) -> Iterator[webvtt.Caption]:
        """Iterate over captions."""
        return iter(self._vtt.captions)

    def __len__(self) -> int:
        """Get the number of captions."""
        return len(self._vtt.captions)

    def __getitem__(self, index: int | slice) -> webvtt.Caption | list[webvtt.Caption]:
        """Get caption(s) by index."""
        return self._vtt.captions[index]

    def filter(self, predicate: Callable[[webvtt.Caption], bool]) -> "Webvtt":
        """Filter captions based on a predicate function."""
        filtered_vtt = webvtt.WebVTT()
        filtered_vtt.captions = [cap for cap in self._vtt.captions if predicate(cap)]

        result = Webvtt.__new__(Webvtt)
        result._vtt = filtered_vtt
        return result

    def map(self, func) -> list[Any]:
        """Map a function over all captions."""
        return [func(cap) for cap in self._vtt.captions]

    def to_webvtt_text(self) -> WebvttText:
        """Convert back to WebVTT text format."""
        return cast_webvtt(self._vtt.content)

    def __str__(self) -> str:
        """String representation returns the WebVTT content."""
        return self._vtt.content

    def __repr__(self) -> str:
        """Repr shows caption count."""
        return f"Webvtt({len(self)} captions)"
