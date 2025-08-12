"""Search functionality for transcripts and other entities."""

import logging
from datetime import datetime
from typing import Annotated, Any, Dict

import sqlalchemy
import webvtt
from pydantic import BaseModel, Field, constr, field_serializer

from reflector.db import database
from reflector.db.transcripts import SourceKind, transcripts
from reflector.db.utils import is_postgresql
from reflector.utils.webvtt_types import Webvtt, WebvttText, parse_webvtt_from_db

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 20
SNIPPET_CONTEXT_LENGTH = 50  # Characters before/after match to include
DEFAULT_SNIPPET_MAX_LENGTH = 150
DEFAULT_MAX_SNIPPETS = 3

SearchQueryBase = constr(min_length=1, strip_whitespace=True)
SearchLimitBase = Annotated[int, Field(ge=1, le=100)]
SearchOffsetBase = Annotated[int, Field(ge=0)]
SearchTotalBase = Annotated[int, Field(ge=0)]

SearchQuery = Annotated[SearchQueryBase, Field(description="Search query text")]
SearchLimit = Annotated[SearchLimitBase, Field(description="Results per page")]
SearchOffset = Annotated[
    SearchOffsetBase, Field(description="Number of results to skip")
]
SearchTotal = Annotated[
    SearchTotalBase, Field(description="Total number of search results")
]


class SearchParameters(BaseModel):
    """Validated search parameters for full-text search."""

    query_text: SearchQuery
    limit: SearchLimit = DEFAULT_SEARCH_LIMIT
    offset: SearchOffset = 0
    user_id: str | None = None
    room_id: str | None = None


class SearchResultDB(BaseModel):
    """Intermediate model for validating raw database results."""

    id: str = Field(..., min_length=1)
    created_at: datetime
    status: str = Field(..., min_length=1)
    duration: float | None = Field(None, ge=0)
    user_id: str | None = None
    title: str | None = None
    source_kind: SourceKind
    room_id: str | None = None
    rank: float = Field(..., ge=0, le=1)


class SearchResult(BaseModel):
    """Public search result model with computed fields."""

    id: str = Field(..., min_length=1)
    title: str | None = None
    user_id: str | None = None
    room_id: str | None = None
    created_at: datetime
    status: str = Field(..., min_length=1)
    rank: float = Field(..., ge=0, le=1)
    duration: float | None = Field(..., ge=0, description="Duration in seconds")
    search_snippets: list[str] = Field(
        description="Text snippets around search matches"
    )

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat()


class SearchController:
    """Controller for search operations across different entities."""

    @staticmethod
    def _extract_webvtt_text(webvtt_content: WebvttText) -> str:
        """Extract plain text from WebVTT content."""
        if not webvtt_content:
            return ""

        vtt = Webvtt(webvtt_content)
        return " ".join(caption.text for caption in vtt.captions if caption.text)

    @staticmethod
    def _generate_webvtt_snippets(
        vtt: Webvtt,
        query: str,
        max_snippets: int = DEFAULT_MAX_SNIPPETS,
        snippet_max_length: int = DEFAULT_SNIPPET_MAX_LENGTH,
    ) -> list[WebvttText]:
        """Generate WebVTT format snippets with surrounding context.

        Returns actual WebVTT formatted snippets that can be parsed/played.
        All captions can be truncated by words to fit max_length.
        Timestamps are NOT adjusted - they remain as original even for truncated text.

        Raises:
            ValueError: If no matches found (indicates a bug as DB already confirmed matches)
            ValueError: If WebVTT is empty (no captions to search)
        """
        if not query:
            raise ValueError("Query cannot be empty")

        if not vtt.captions:
            raise ValueError("Empty WebVTT - no captions to search")

        query_lower = query.lower()

        # Find all matches with their caption indices
        matches = []
        for i, caption in enumerate(vtt.captions):
            if not caption.text:
                continue

            text_lower = caption.text.lower()
            if query_lower in text_lower:
                matches.append(i)

        if not matches:
            raise ValueError(
                f"No matches found for '{query}' - this indicates a bug as "
                "database already confirmed matches exist"
            )

        # Group nearby matches into snippet ranges
        snippet_ranges = []
        current_range_start = matches[0]
        current_range_end = matches[0]

        for match_idx in matches[1:]:
            # If match is within 2 captions of current range, extend it
            if match_idx <= current_range_end + 2:
                current_range_end = match_idx
            else:
                # Save current range and start new one
                snippet_ranges.append((current_range_start, current_range_end))
                current_range_start = match_idx
                current_range_end = match_idx

                if len(snippet_ranges) >= max_snippets:
                    break

        # Add the last range
        if len(snippet_ranges) < max_snippets:
            snippet_ranges.append((current_range_start, current_range_end))

        # Build WebVTT snippets for each range
        snippets = []
        for range_start, range_end in snippet_ranges[:max_snippets]:
            # Determine context window (1 caption before/after)
            snippet_start = max(0, range_start - 1)
            snippet_end = min(len(vtt.captions) - 1, range_end + 1)

            # Create new WebVTT for this snippet
            snippet_vtt = webvtt.WebVTT()

            # We only care about textual content length, not WebVTT format overhead
            # Calculate how many captions we're including
            num_captions = snippet_end - snippet_start + 1

            # Simple budget distribution - each caption gets equal share
            budget_per_caption = (
                snippet_max_length // num_captions
                if num_captions > 0
                else snippet_max_length
            )

            # Identify which are match captions
            match_indices = [
                i for i in range(snippet_start, snippet_end + 1) if i in matches
            ]

            # Build captions for snippet
            for i in range(snippet_start, snippet_end + 1):
                original_caption = vtt.captions[i]

                # Determine if we need to truncate this caption
                # Match captions can also be truncated if needed
                is_match = i in match_indices
                is_before = i < match_indices[0] if match_indices else False
                is_after = i > match_indices[-1] if match_indices else False

                # Truncate if text exceeds budget
                if len(original_caption.text) > budget_per_caption:
                    truncated_text = SearchController._truncate_caption_text(
                        original_caption.text,
                        budget_per_caption,
                        is_before=is_before,
                        is_after=is_after,
                        is_match=is_match,
                        query=query if is_match else None,
                    )
                else:
                    truncated_text = original_caption.text

                # Keep original timestamps - NO adjustment even for truncated text
                new_caption = webvtt.Caption(
                    start=original_caption.start,
                    end=original_caption.end,
                    text=f"<v {original_caption.voice}>{truncated_text}"
                    if original_caption.voice
                    else truncated_text,
                )

                snippet_vtt.captions.append(new_caption)

            # Convert to WebvttText
            from reflector.utils.webvtt_types import cast_webvtt

            snippets.append(cast_webvtt(snippet_vtt.content))

        return snippets

    @staticmethod
    def _truncate_caption_text(
        text: str,
        max_length: int,
        is_before: bool = False,
        is_after: bool = False,
        is_match: bool = False,
        query: str | None = None,
    ) -> str:
        """Truncate caption text at word boundaries.

        Args:
            text: Original caption text
            max_length: Maximum length for truncated text
            is_before: If True, keep end of text (truncate from start)
            is_after: If True, keep start of text (truncate from end)
            is_match: If True, this caption contains the match
            query: The search query (used to preserve match in truncation)
        """
        if len(text) <= max_length:
            return text

        words = text.split()

        # If this is a match caption, try to preserve the match
        if is_match and query:
            query_lower = query.lower()
            text_lower = text.lower()
            match_pos = text_lower.find(query_lower)

            if match_pos >= 0:
                # Try to center the truncation around the match
                match_end = match_pos + len(query_lower)

                # Calculate how much context we can include around the match
                remaining_budget = (
                    max_length - len(query) - 6
                )  # 6 for "..." on both sides
                if remaining_budget > 0:
                    context_each_side = remaining_budget // 2

                    # Find word boundaries
                    start_pos = max(0, match_pos - context_each_side)
                    end_pos = min(len(text), match_end + context_each_side)

                    # Adjust to word boundaries
                    while start_pos > 0 and text[start_pos - 1] != " ":
                        start_pos -= 1
                    while end_pos < len(text) and text[end_pos] != " ":
                        end_pos += 1

                    result = text[start_pos:end_pos].strip()
                    if start_pos > 0:
                        result = "..." + result
                    if end_pos < len(text):
                        result = result + "..."

                    return result

        if is_before:
            # Keep last words for context before match
            result_words = []
            total_length = 0
            for word in reversed(words):
                word_length = len(word) + 1  # +1 for space
                if total_length + word_length + 3 <= max_length:  # +3 for "..."
                    result_words.append(word)
                    total_length += word_length
                else:
                    break

            if result_words:
                return "..." + " ".join(reversed(result_words))
            else:
                # At least show something
                return "..." + words[-1][: max_length - 3]

        elif is_after:
            # Keep first words for context after match
            result_words = []
            total_length = 0
            for word in words:
                word_length = len(word) + 1  # +1 for space
                if total_length + word_length + 3 <= max_length:  # +3 for "..."
                    result_words.append(word)
                    total_length += word_length
                else:
                    break

            if result_words:
                return " ".join(result_words) + "..."
            else:
                # At least show something
                return words[0][: max_length - 3] + "..."

        else:
            # Middle truncation (shouldn't happen in our use case)
            if max_length > 6:
                half = (max_length - 3) // 2
                return text[:half] + "..." + text[-half:]
            else:
                return text[:max_length]

    @staticmethod
    def _format_timestamp(timestamp: str) -> str:
        """Format timestamp for display in snippet."""
        try:
            # Convert "00:00:15.000" to "0:15"
            parts = timestamp.split(":")
            if len(parts) >= 2:
                hours = int(parts[0]) if parts[0].isdigit() else 0
                minutes = int(parts[1]) if parts[1].isdigit() else 0
                if len(parts) > 2:
                    sec_parts = parts[2].split(".")
                    seconds = int(sec_parts[0]) if sec_parts[0].isdigit() else 0
                else:
                    seconds = 0

                if hours > 0:
                    return f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    return f"{minutes}:{seconds:02d}"
        except (ValueError, IndexError):
            pass
        return timestamp  # Return original if parsing fails

    @classmethod
    async def search_transcripts(
        cls, params: SearchParameters
    ) -> tuple[list[SearchResult], int]:
        """
        Full-text search for transcripts using PostgreSQL tsvector.
        Returns (results, total_count).
        """

        if not is_postgresql():
            logger.warning(
                "Full-text search requires PostgreSQL. Returning empty results."
            )
            return [], 0

        search_query = sqlalchemy.func.websearch_to_tsquery(
            "english", params.query_text
        )

        base_query = sqlalchemy.select(
            [
                transcripts.c.id,
                transcripts.c.title,
                transcripts.c.created_at,
                transcripts.c.duration,
                transcripts.c.status,
                transcripts.c.user_id,
                transcripts.c.room_id,
                transcripts.c.source_kind,
                transcripts.c.webvtt,
                sqlalchemy.func.ts_rank(
                    transcripts.c.search_vector_en,
                    search_query,
                    32,  # normalization flag: rank/(rank+1) for 0-1 range
                ).label("rank"),
            ]
        ).where(transcripts.c.search_vector_en.op("@@")(search_query))

        if params.user_id:
            base_query = base_query.where(transcripts.c.user_id == params.user_id)
        if params.room_id:
            base_query = base_query.where(transcripts.c.room_id == params.room_id)

        query = (
            base_query.order_by(sqlalchemy.desc(sqlalchemy.text("rank")))
            .limit(params.limit)
            .offset(params.offset)
        )
        rs = await database.fetch_all(query)

        count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            base_query.alias("search_results")
        )
        total = await database.fetch_val(count_query)

        def _process_result(r) -> SearchResult:
            r_dict: Dict[str, Any] = dict(r)
            webvtt_raw: str | None = r_dict.pop("webvtt", None)
            db_result = SearchResultDB.model_validate(r_dict)

            snippets = []
            if webvtt_raw:
                try:
                    webvtt_text = parse_webvtt_from_db(webvtt_raw)
                    vtt = Webvtt(webvtt_text)
                    # Use the new WebVTT-aware snippet generation
                    webvtt_snippets = cls._generate_webvtt_snippets(
                        vtt, params.query_text
                    )
                    # Convert WebvttText to str for SearchResult
                    snippets = [str(s) for s in webvtt_snippets]
                except ValueError as e:
                    logger.warning(
                        f"Invalid WebVTT content in transcript {r_dict.get('id')}",
                        exc_info=e,
                    )

            return SearchResult(**db_result.model_dump(), search_snippets=snippets)

        results = [_process_result(r) for r in rs]
        return results, total


search_controller = SearchController()
