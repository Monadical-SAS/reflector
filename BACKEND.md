# Backend Search API Enhancement Requirements

## Overview
The frontend search interface has been upgraded with an Algolia-style progressive disclosure UI that requires additional filtering capabilities in the `/v1/transcripts/search` endpoint. Currently, the search API only supports basic text search with limited filtering, while the UI expects more comprehensive filtering options.

## Current API Status

### Existing `/v1/transcripts/search` Endpoint
**Method:** GET
**Current Parameters:**
- `q` (string, required) - Search query text
- `limit` (number, optional) - Results per page (default: 20)
- `offset` (number, optional) - Number of results to skip (default: 0)
- `roomId` (string | null, optional) - Single room ID filter ✅ **WORKING IN FRONTEND**

**Response:** `SearchResponse` with `SearchResult[]` containing:
- `id` (string)
- `title` (string | null)
- `user_id` (string | null)
- `room_id` (string | null)
- `created_at` (string)
- `status` (string)
- `rank` (number) - Relevance score 0-1
- `duration` (number | null) - Duration in seconds
- `search_snippets` (string[]) - Text snippets with search matches

## Required Enhancements

### 1. Add Missing Filter Parameters

The search endpoint needs to support the following additional parameters to match the frontend filtering capabilities:

#### Source Kind Filter
**Parameter:** `source_kind`
**Type:** string (enum: "live" | "file" | "room" | "whereby")
**Description:** Filter results by transcript source type
**Implementation Note:** This field exists in the transcript model and is already used by `/v1/transcripts` list endpoint

#### Status Filter
**Parameter:** `status`
**Type:** string or comma-separated string for multiple values
**Values:** "completed" | "processing" | "failed" | "pending"
**Description:** Filter results by processing status
**Implementation Note:** Consider supporting multiple statuses via comma separation (e.g., `status=completed,processing`)

#### Date Range Filters
**Parameters:**
- `date_from` (string, ISO 8601 format)
- `date_to` (string, ISO 8601 format)

**Description:** Filter results by creation date range
**Implementation Note:** Should filter on `created_at` field

#### User Filter
**Parameter:** `user_id`
**Type:** string
**Description:** Filter results by user ID (for admin/multi-user scenarios)

#### Multiple Room IDs
**Parameter:** `room_ids` (replace single `roomId`)
**Type:** comma-separated string
**Description:** Support filtering by multiple room IDs
**Example:** `room_ids=room1,room2,room3`

### 2. Add Missing Response Fields

The `SearchResult` type should include:
- `source_kind` (string) - Currently missing but needed for UI badges
- `room_name` (string | null) - For displaying room information
- `processing_status` (string) - More detailed than just "status"

### 3. Search Behavior Enhancements

#### Full-Text Search Scope
Ensure the search (`q` parameter) searches across:
- Transcript title
- Transcript content/text
- Speaker names
- Topic summaries (if available)
- Room names

#### Snippet Generation
- Ensure snippets have proper context (include surrounding sentences)
- Preserve HTML `<mark>` tags for highlighting matched terms
- Return 3-5 most relevant snippets per result
- Sort snippets by relevance within each result

#### Relevance Ranking
The `rank` field (0-1 score) should consider:
- Text match quality (exact vs fuzzy)
- Match location (title > summary > content)
- Match frequency
- Recency (newer transcripts slightly preferred)

## Example API Calls

### Basic Search
```
GET /v1/transcripts/search?q=meeting&limit=20&offset=0
```

### Search with Filters (After Enhancement)
```
GET /v1/transcripts/search?
  q=product%20roadmap&
  source_kind=live&
  room_ids=engineering,product&
  status=completed&
  date_from=2024-01-01T00:00:00Z&
  date_to=2024-01-31T23:59:59Z&
  limit=20&
  offset=0
```

## Migration Notes

### Backward Compatibility
- Keep the existing `roomId` parameter working (map to `room_ids` internally)
- Make all new parameters optional to maintain compatibility

### Database Considerations
- Ensure proper indexes exist for:
  - Full-text search fields
  - `source_kind`
  - `status`
  - `created_at`
  - `room_id`
  - `user_id`

### Performance Optimization
- Consider implementing search result caching (5-10 minute TTL)
- Use PostgreSQL full-text search features if not already implemented
- Consider pagination limits (max 100 results per page)

## Testing Requirements

1. **Filter Combinations**: Test various filter combinations work correctly
2. **Search Relevance**: Verify ranking algorithm produces sensible results
3. **Performance**: Ensure search remains fast with large datasets (< 500ms for most queries)
4. **Edge Cases**:
   - Empty search query with filters only
   - No results scenarios
   - Special characters in search queries
   - Very long search queries

## Implementation Priority

**High Priority** (Needed for current UI):
1. `source_kind` parameter and response field
2. Multiple room IDs support (`room_ids`)
3. `status` filter

**Medium Priority** (Enhances functionality):
1. Date range filters
2. Enhanced snippet generation
3. Room name in response

**Low Priority** (Nice to have):
1. User ID filter
2. Advanced relevance tuning
3. Search result caching

## Notes for Frontend Integration

### Current Status (December 2024)
- ✅ **Room filter is working** - The frontend now properly passes `roomId` to the search API
- ✅ **Visual feedback implemented** - Active filters show as badges during search
- ✅ **Filter persistence** - Filters remain active when searching

### Once Backend Enhancements are Complete
The frontend's `useSearchTranscripts` hook can be updated to:
1. Pass all additional filter parameters to the API (source_kind, status, date ranges)
2. Remove fallback to regular list API for filtered browsing
3. Enable all filter UI elements to be functional during search

The frontend is already prepared to handle these parameters - they just need to be supported by the backend API.