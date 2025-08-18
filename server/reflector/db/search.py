"""Search functionality for transcripts and other entities."""

import asyncio
import itertools
import logging
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from typing import Annotated, Any, Dict, Iterator, cast

import sqlalchemy
import webvtt
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError, constr, field_serializer
from pydantic.v1 import NonNegativeFloat, NonNegativeInt
from sqlalchemy.exc import DatabaseError, OperationalError

from reflector.db import get_database
from reflector.db.rooms import rooms
from reflector.db.transcripts import SourceKind, transcripts
from reflector.db.utils import is_postgresql

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 20
SNIPPET_CONTEXT_LENGTH = 50  # Characters before/after match to include
DEFAULT_SNIPPET_MAX_LENGTH = cast(NonNegativeInt, 150)
DEFAULT_MAX_SNIPPETS = cast(NonNegativeInt, 3)
LONG_SUMMARY_MAX_SNIPPETS = 2

SearchQueryBase = constr(min_length=0, strip_whitespace=True)
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

WEBVTT_SPEC_HEADER = "WEBVTT\n\n"

WebVTTContent = Annotated[
    str,
    Field(min_length=len(WEBVTT_SPEC_HEADER), description="WebVTT content"),
]


def parse_webvtt(raw_content: str) -> WebVTTContent:
    """Parse WebVTT content and return it as a string."""
    if not raw_content.startswith(WEBVTT_SPEC_HEADER):
        raise ValueError(f"Invalid WebVTT content, no header {WEBVTT_SPEC_HEADER}")
    return raw_content


@dataclass(frozen=True)
class SnippetCandidate:
    """Represents a candidate snippet with its position."""

    _text: str
    start: NonNegativeInt
    _original_text_length: int

    @property
    def end(self) -> NonNegativeInt:
        """Calculate end position from start and raw text length."""
        return self.start + len(self._text)

    def text(self) -> str:
        """Get display text with ellipses added if needed."""
        result = self._text.strip()
        if self.start > 0:
            result = "..." + result
        if self.end < self._original_text_length:
            result = result + "..."
        return result


class SearchParameters(BaseModel):
    """Validated search parameters for full-text search."""

    query_text: SearchQuery
    limit: SearchLimit = DEFAULT_SEARCH_LIMIT
    offset: SearchOffset = 0
    user_id: str | None = None
    room_id: str | None = None
    source_kind: SourceKind | None = None


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
    room_name: str | None = None
    source_kind: SourceKind
    created_at: datetime
    status: str = Field(..., min_length=1)
    rank: float = Field(..., ge=0, le=1)
    duration: NonNegativeFloat | None = Field(..., description="Duration in seconds")
    search_snippets: list[str] = Field(
        description="Text snippets around search matches"
    )
    total_match_count: NonNegativeInt = Field(
        default=0, description="Total number of matches found in the transcript"
    )

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat()


def extract_webvtt_text(webvtt_content: WebVTTContent) -> str:
    """Extract plain text from WebVTT content using webvtt library."""
    try:
        buffer = StringIO(webvtt_content)
        vtt = webvtt.read_buffer(buffer)
        return " ".join(caption.text for caption in vtt if caption.text)
    except webvtt.errors.MalformedFileError as e:
        logger.warning(f"Malformed WebVTT content: {e}")
        return ""
    except (UnicodeDecodeError, ValueError) as e:
        logger.warning(f"Failed to decode WebVTT content: {e}")
        return ""
    except AttributeError as e:
        logger.error(f"WebVTT parsing error - unexpected format: {e}", exc_info=True)
        return ""
    except Exception as e:
        logger.error(f"Unexpected error parsing WebVTT: {e}", exc_info=True)
        return ""


def find_all_matches(text: str, query: str) -> Iterator[int]:
    """Generate all match positions for a query in text."""
    if not text:
        logger.warning("Empty text for search query in find_all_matches")
        return
    if not query:
        logger.warning("Empty query for search text in find_all_matches")
        return

    text_lower = text.lower()
    query_lower = query.lower()
    start = 0

    while (pos := text_lower.find(query_lower, start)) != -1:
        yield pos
        start = pos + len(query_lower)


def count_matches(text: str, query: str) -> NonNegativeInt:
    """Count total number of matches for a query in text."""
    ZERO = cast(NonNegativeInt, 0)
    if not text:
        logger.warning("Empty text for search query in count_matches")
        return ZERO
    if not query:
        logger.warning("Empty query for search text in count_matches")
        return ZERO
    return cast(NonNegativeInt, sum(1 for _ in find_all_matches(text, query)))


def create_snippet(
    text: str, match_pos: int, max_length: int = DEFAULT_SNIPPET_MAX_LENGTH
) -> SnippetCandidate:
    """Create a snippet from a match position."""
    snippet_start = cast(NonNegativeInt, max(0, match_pos - SNIPPET_CONTEXT_LENGTH))
    snippet_end = min(len(text), match_pos + max_length - SNIPPET_CONTEXT_LENGTH)

    snippet_text = text[snippet_start:snippet_end]

    return SnippetCandidate(
        _text=snippet_text, start=snippet_start, _original_text_length=len(text)
    )


def filter_non_overlapping_snippets(
    candidates: Iterator[SnippetCandidate],
) -> Iterator[str]:
    """Filter out overlapping snippets and return only display text."""
    last_end = 0
    for candidate in candidates:
        display_text = candidate.text()
        # it means that next overlapping snippets simply don't get included
        # it's fine as simplistic logic and users probably won't care much because they already have their search results just fin
        if candidate.start >= last_end and display_text:
            yield display_text
            last_end = candidate.end


def generate_snippets(
    text: str,
    query: str,
    max_length: NonNegativeInt = DEFAULT_SNIPPET_MAX_LENGTH,
    max_snippets: NonNegativeInt = DEFAULT_MAX_SNIPPETS,
) -> list[str]:
    if not text or not query:
        logger.warning("Empty text or query for generate_snippets")
        return []

    candidates = (
        create_snippet(text, pos, max_length) for pos in find_all_matches(text, query)
    )
    filtered = filter_non_overlapping_snippets(candidates)
    snippets = list(itertools.islice(filtered, max_snippets))

    # Fallback to first word search if no full matches
    # it's another assumption: proper snippet logic generation is quite complicated and tied to db logic, so simplification is used here
    if not snippets and " " in query:
        first_word = query.split()[0]
        return generate_snippets(text, first_word, max_length, max_snippets)

    return snippets


class SearchController:
    """Controller for search operations across different entities."""

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

        if params.query_text:
            search_query = sqlalchemy.func.websearch_to_tsquery(
                "english", params.query_text
            )

            base_query = (
                sqlalchemy.select(
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
                        transcripts.c.long_summary,
                        sqlalchemy.case(
                            (
                                transcripts.c.room_id.isnot(None)
                                & rooms.c.id.is_(None),
                                "Deleted Room",
                            ),
                            else_=rooms.c.name,
                        ).label("room_name"),
                        sqlalchemy.func.ts_rank(
                            transcripts.c.search_vector_en,
                            search_query,
                            32,  # normalization flag: rank/(rank+1) for 0-1 range
                        ).label("rank"),
                    ]
                )
                .select_from(
                    transcripts.join(
                        rooms, transcripts.c.room_id == rooms.c.id, isouter=True
                    )
                )
                .where(transcripts.c.search_vector_en.op("@@")(search_query))
            )
        else:
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
                    transcripts.c.long_summary,
                    sqlalchemy.case(
                        (
                            transcripts.c.room_id.isnot(None) & rooms.c.id.is_(None),
                            "Deleted Room",
                        ),
                        else_=rooms.c.name,
                    ).label("room_name"),
                    sqlalchemy.cast(1.0, sqlalchemy.Float).label("rank"),
                ]
            ).select_from(
                transcripts.join(
                    rooms, transcripts.c.room_id == rooms.c.id, isouter=True
                )
            )

        if params.user_id:
            base_query = base_query.where(transcripts.c.user_id == params.user_id)
        if params.room_id:
            base_query = base_query.where(transcripts.c.room_id == params.room_id)
        if params.source_kind:
            base_query = base_query.where(
                transcripts.c.source_kind == params.source_kind
            )

        if params.query_text:
            order_by = sqlalchemy.desc(sqlalchemy.text("rank"))
        else:
            order_by = sqlalchemy.desc(transcripts.c.created_at)

        query = base_query.order_by(order_by).limit(params.limit).offset(params.offset)

        try:
            rs = await asyncio.wait_for(get_database().fetch_all(query), timeout=10.0)

            count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
                base_query.alias("search_results")
            )
            total = await asyncio.wait_for(
                get_database().fetch_val(count_query), timeout=5.0
            )
        except asyncio.TimeoutError as e:
            logger.error(f"Search query timeout for: {params.query_text}")
            raise HTTPException(status_code=504, detail="Search query timed out") from e
        except (DatabaseError, OperationalError) as e:
            logger.error(f"Database error during search: {e}", exc_info=True)
            raise HTTPException(
                status_code=503, detail="Database temporarily unavailable"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected search error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Internal server error during search"
            ) from e

        def _process_result(r) -> SearchResult:
            r_dict: Dict[str, Any] = dict(r)
            webvtt_raw: str | None = r_dict.pop("webvtt", None)
            if webvtt_raw:
                webvtt = parse_webvtt(webvtt_raw)
            else:
                webvtt = None
            long_summary: str | None = r_dict.pop("long_summary", None)
            room_name: str | None = r_dict.pop("room_name", None)
            db_result = SearchResultDB.model_validate(r_dict)

            snippets, total_match_count = combine_snippet_sources(
                long_summary, webvtt, params.query_text, DEFAULT_MAX_SNIPPETS
            )

            return SearchResult(
                **db_result.model_dump(),
                room_name=room_name,
                search_snippets=snippets,
                total_match_count=total_match_count,
            )

        try:
            results = [_process_result(r) for r in rs]
        except ValidationError as e:
            logger.error(f"Invalid search result data: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Internal search result data consistency error"
            )
        except Exception as e:
            logger.error(f"Error processing search results: {e}", exc_info=True)
            raise

        return results, total


def generate_webvtt_snippets(
    webvtt_content: WebVTTContent,
    query: str,
    max_snippets: NonNegativeInt = DEFAULT_MAX_SNIPPETS,
) -> list[str]:
    """Generate snippets from WebVTT content."""
    plain_text = extract_webvtt_text(webvtt_content)
    return generate_snippets(plain_text, query, max_snippets=max_snippets)


def generate_summary_snippets(
    summary: str, query: str, max_snippets: NonNegativeInt = LONG_SUMMARY_MAX_SNIPPETS
) -> list[str]:
    """Generate snippets from summary text."""
    return generate_snippets(summary, query, max_snippets=max_snippets)


def combine_snippet_sources(
    summary: str | None,
    webvtt: WebVTTContent | None,
    query: str,
    max_total: NonNegativeInt = DEFAULT_MAX_SNIPPETS,
) -> tuple[list[str], NonNegativeInt]:
    """Combine snippets from multiple sources and return total match count.

    Returns (snippets, total_match_count) tuple.

    snippets can be empty for real in case of e.g. title match
    """
    webvtt_matches = 0
    summary_matches = 0

    if webvtt:
        webvtt_text = extract_webvtt_text(webvtt)
        webvtt_matches = count_matches(webvtt_text, query)

    if summary:
        summary_matches = count_matches(summary, query)

    total_matches = cast(NonNegativeInt, webvtt_matches + summary_matches)

    summary_snippets = generate_summary_snippets(summary, query) if summary else []

    if len(summary_snippets) >= max_total:
        return summary_snippets[:max_total], total_matches

    remaining = max_total - len(summary_snippets)
    webvtt_snippets = (
        generate_webvtt_snippets(webvtt, query, remaining) if webvtt else []
    )

    return summary_snippets + webvtt_snippets, total_matches


search_controller = SearchController()
