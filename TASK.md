# TASK: Add Search API Endpoint

## Objective
Expose the existing `search_full_text` method from `TranscriptController` as a REST API endpoint. The search functionality is already implemented at the database layer - we need to create a proper API layer on top of it.

## Current State Analysis

### Existing Components
1. **Database Layer** (`server/reflector/db/transcripts.py`):
   - `TranscriptController.search_full_text()` method fully implemented
   - Returns `tuple[list[SearchResult], int]` (results + total count)
   - PostgreSQL-only with SQLite graceful degradation
   - Branded types already defined:
     - `SearchQuery`: Annotated[str, Field(min_length=3)]
     - `SearchLimit`: Annotated[int, Field(ge=1, le=100)]
     - `SearchOffset`: Annotated[int, Field(ge=0)]
   - `SearchResult` model extends `TranscriptBase` with `rank` field

2. **Search Infrastructure**:
   - Full-text search vector (`search_vector_en`) already in database
   - GIN index configured for performance
   - WebVTT column populated automatically from topics
   - Search uses `websearch_to_tsquery` for advanced syntax support

3. **Existing API Pattern** (`server/reflector/views/transcripts.py`):
   - Current list endpoint: `GET /v1/transcripts?search_term=...` (uses ILIKE)
   - Authentication via `auth.current_user_optional`
   - Pagination via `fastapi_pagination`

## Implementation Requirements

### 1. Create New Search Endpoint

**Endpoint**: `GET /v1/transcripts/search`

**Request Parameters**:
```python
q: SearchQuery          # Query text (min 3 chars), uses branded type
limit: SearchLimit = 20  # Results per page (1-100), uses branded type  
offset: SearchOffset = 0 # Pagination offset (>=0), uses branded type
room_id: Optional[str] = None  # Filter by room
```

**Response Model**:
```python
# Define branded type for total count
SearchTotal = Annotated[int, Field(ge=0, description="Total number of search results")]

class SearchResponse(BaseModel):
    results: list[SearchResult]  # Uses existing SearchResult model
    total: SearchTotal           # Total count (branded type)
    query: SearchQuery            # Echo back the query (branded type)
    limit: SearchLimit           # Echo back limit (branded type)
    offset: SearchOffset          # Echo back offset (branded type)
```

### 2. Authentication & Authorization
- Use existing `auth.current_user_optional` dependency
- Pass `user_id` from auth context to `search_full_text()`
- Respect PUBLIC_MODE setting (401 if not authenticated and not public)

### 3. Error Handling (Automatic via FastAPI + Pydantic)
- **HTTP 422 Unprocessable Entity**: Automatically returned for validation failures
  - Query < 3 chars: `{"detail": [{"type": "string_too_short", "loc": ["query", "q"], "msg": "String should have at least 3 characters"}]}`
  - Invalid limit/offset: Similar structured error with constraint details
- **HTTP 200**: Empty results for SQLite (controller handles logging)
- **HTTP 401/403**: Standard auth errors

### 4. Implementation Details

**File**: `server/reflector/views/transcripts.py`

Add to existing router:

```python
from fastapi import Query
from reflector.db.transcripts import (
    SearchResult,
    # ... existing imports
)

# Define branded types for API layer (FastAPI Query validates automatically)
SearchQuery = Annotated[str, Query(min_length=3, description="Search query text")]
SearchLimit = Annotated[int, Query(ge=1, le=100, description="Results per page")]
SearchOffset = Annotated[int, Query(ge=0, description="Number of results to skip")]
SearchTotal = Annotated[int, Field(ge=0, description="Total number of search results")]

class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: SearchTotal
    query: str  # Plain string in response
    limit: int  # Plain int in response
    offset: int  # Plain int in response

@router.get("/transcripts/search", response_model=SearchResponse)
async def transcripts_search(
    q: SearchQuery,  # Branded type with automatic validation
    limit: SearchLimit = 20,  # Branded type with automatic validation
    offset: SearchOffset = 0,  # Branded type with automatic validation
    room_id: Optional[str] = None,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    """
    Full-text search across transcript titles and content.
    
    Supports advanced query syntax:
    - OR operator: "meeting OR workshop"
    - Exclusion: "meeting -budget"  
    - Phrases: '"quarterly review"'
    
    Note: Requires PostgreSQL. Returns empty results on SQLite.
    """
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = user["sub"] if user else None
    
    # NO VALIDATION HERE - FastAPI already guaranteed:
    # - q has min_length=3
    # - limit is 1-100
    # - offset is >= 0
    # Just pass the parsed values directly
    results, total = await transcripts_controller.search_full_text(
        query_text=q,  # Already validated by FastAPI
        user_id=user_id,
        limit=limit,    # Already validated by FastAPI
        offset=offset,  # Already validated by FastAPI
        room_id=room_id
    )
    
    return SearchResponse(
        results=results,
        total=total,
        query=q,
        limit=limit,
        offset=offset
    )
```

## Testing Checklist

### Manual Testing
1. ✅ Query validation (< 3 chars returns 400)
2. ✅ Basic search returns results
3. ✅ Pagination works (offset/limit)
4. ✅ Room filtering works
5. ✅ User filtering (authenticated vs anonymous)
6. ✅ Advanced syntax (OR, -, quotes)
7. ✅ SQLite returns empty results with log
8. ✅ PostgreSQL returns ranked results

### Automated Tests
- Existing tests in `server/tests/test_search.py` cover controller
- Add API-level tests for endpoint validation

## Implementation Notes

### CRITICAL: Parse Don't Validate with FastAPI

**Reference**: See `server/docs/API_TYPES.md` for detailed explanation of Parse Don't Validate principle and branded types.

The implementation follows the "Parse Don't Validate" principle:

1. **Query Parameters as Parsers**: Using `Annotated[type, Query(...)]` creates parsers, not just validators
2. **Automatic Validation**: FastAPI validates BEFORE the function is called - returns HTTP 422 on failure
3. **Type Transformation**: Raw query strings are parsed into typed, validated objects
4. **Knowledge Preservation**: Once parsed, the types carry proof of validity

### Branded Types for API Layer

We define API-specific branded types using `Query()` for automatic validation:
- `SearchQuery = Annotated[str, Query(min_length=3)]` - Parses and validates query length
- `SearchLimit = Annotated[int, Query(ge=1, le=100)]` - Parses and validates bounds
- `SearchOffset = Annotated[int, Query(ge=0)]` - Parses and validates non-negative

These are **different** from the database layer types but serve the same purpose at the API boundary.

### ⚠️ IMPORTANT: No Re-validation

**DO NOT re-check constraints inside the function**. Once FastAPI has parsed the parameters:
- `q` is GUARANTEED to be at least 3 characters
- `limit` is GUARANTEED to be between 1-100
- `offset` is GUARANTEED to be >= 0

Any re-checking like `if len(q) < 3` is redundant and violates Parse Don't Validate. The controller's assertions are for internal API contracts, not for re-validating already-parsed data.

### Why Not Modify Existing Endpoint?
The existing `/v1/transcripts?search_term=...` uses ILIKE for simple title search. We're adding a new endpoint because:
1. Full-text search has different semantics (ranking, advanced syntax)
2. Returns different response structure (includes total count)
3. Backwards compatibility - existing clients continue working
4. Clear separation of simple vs advanced search

### Future Considerations (NOT IN SCOPE)
- Search snippets/highlights (PRD mentions but not implemented in controller)
- Search filters by date/duration
- Search suggestions/autocomplete
- Faceted search results

## Success Criteria
1. ✅ New endpoint accessible at `/v1/transcripts/search`
2. ✅ All branded types used correctly (no raw types)
3. ✅ Authentication properly enforced
4. ✅ PostgreSQL returns ranked results
5. ✅ SQLite gracefully returns empty results
6. ✅ OpenAPI documentation generated correctly
7. ✅ Response includes pagination metadata