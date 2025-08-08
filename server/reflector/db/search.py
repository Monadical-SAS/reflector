"""Search functionality for transcripts and other entities."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Dict

import sqlalchemy
from pydantic import BaseModel, Field, field_serializer, field_validator

from reflector.db import database
from reflector.db.transcripts import transcripts
from reflector.db.utils import is_postgresql

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 20
DEFAULT_SNIPPET_MAX_LENGTH = 150
DEFAULT_MAX_SNIPPETS = 3

SearchQueryBase = Annotated[str, Field(min_length=1)]
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

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """Validate that query text is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()


class SearchResultDB(BaseModel):
    """Intermediate model for validating raw database results."""

    id: str = Field(..., min_length=1)
    created_at: datetime
    status: str = Field(..., min_length=1)
    duration: float | None = Field(None, ge=0)
    user_id: str | None = None
    title: str | None = None
    source_kind: str  # Store as string to avoid circular import
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
    def _extract_webvtt_text(webvtt_content: str) -> str:
        """Extract plain text from WebVTT content."""
        lines = webvtt_content.split("\n")
        text_lines = []
        for line in lines:
            line = line.strip()
            if not line or line == "WEBVTT" or "-->" in line or line.startswith("NOTE"):
                continue
            if line[0:1].isdigit() and ":" in line[:8]:
                continue
            text_lines.append(line)
        return " ".join(text_lines)

    @staticmethod
    def _generate_snippets(
        text: str,
        q: SearchQuery,
        max_length: int = DEFAULT_SNIPPET_MAX_LENGTH,
        max_snippets: int = DEFAULT_MAX_SNIPPETS,
    ) -> list[str]:
        """Generate multiple snippets around all occurrences of search term."""
        if not text or not q:
            return []

        snippets = []
        lower_text = text.lower()
        search_lower = q.lower()

        start_pos = 0
        while len(snippets) < max_snippets:
            pos = lower_text.find(search_lower, start_pos)
            if pos == -1:
                break

            start = max(0, pos - max_length // 2)
            end = min(len(text), pos + len(q) + max_length // 2)

            snippet = text[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."

            snippets.append(snippet)
            start_pos = pos + len(q)

        return snippets

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

        base_query = sqlalchemy.select([
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
        ]).where(transcripts.c.search_vector_en.op("@@")(search_query))

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

        # Process results
        def _process_result(r) -> SearchResult:
            r_dict: Dict[str, Any] = dict(r)
            webvtt: str | None = r_dict.pop("webvtt", None)
            db_result = SearchResultDB.model_validate(r_dict)

            snippets = []
            if webvtt:
                plain_text = cls._extract_webvtt_text(webvtt)
                snippets = cls._generate_snippets(plain_text, params.query_text)

            return SearchResult(**db_result.model_dump(), search_snippets=snippets)

        results = [_process_result(r) for r in rs]
        return results, total


search_controller = SearchController()
