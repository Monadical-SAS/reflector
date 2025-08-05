# Product Requirements Document: Search Revamp

## Executive Summary

Enable full-text search across transcript titles, summaries, and transcript content to improve discoverability of meetings and conversations in Reflector.

## Current State

### Search Functionality
- **Scope**: Limited to transcript titles only
- **Implementation**: SQL `ILIKE` pattern matching (`WHERE title ILIKE '%search_term%'`)
- **Database Support**: SQLite (development), PostgreSQL (production)
- **UI**: Simple search bar in the browse page with table/card view toggle
- **API**: `/v1/transcripts?search_term=...` query parameter

### Data Structure
- **Transcript storage**: Title and summaries as direct columns
- **Content storage**: Transcript text stored within `topics` JSON array as `topics[].transcript`
- **Events**: Audit log only, not used for display

### User Experience
- Users must remember exact title wording to find transcripts
- No ability to search meeting content or summaries
- No indication of where matches were found
- Basic list view with no search context

## Problem Statement

Users cannot effectively find relevant transcripts when they remember the content discussed but not the exact title. This severely limits the value of the transcript archive for knowledge retrieval and meeting follow-up.

## Proposed Solution

### 1. Multi-Field Search

Enable searching across multiple transcript fields:
- **Title** (existing)
- **Short Summary** 
- **Long Summary**
- **Transcript Content** (text within topics)

### 2. Database Implementation

#### PostgreSQL Only
Full-text search is a PostgreSQL-only feature. SQLite will log a warning and return empty results.

TODO english hardcode - RETHINK

TODO first add 'dupe' (from topic column) column for transcript (ILIKE on it)

TODO the transcript is webvtt

Igor []

```sql
search_vector_en tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(short_summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(long_summary, '')), 'C') ||
        setweight(to_tsvector('english', coalesce(array_to_string(topics, ' '), '')), 'D')
    ) STORED
```

NOTE for search we use websearch_to_tsquery

#### SQLite Handling

```python
# In transcripts_controller.get_all()
if search_term and database.url.dialect != "postgresql":
    logger.warning("Search functionality requires PostgreSQL. Returning empty results.")
    return []
```

- Log clear warning message
- Return empty results
- No error thrown - graceful degradation

### 3. API Enhancements

#### Request
No changes - keep existing endpoint:
```
GET /v1/transcripts?search_term=machine+learning&page=1 - KEEP FOR NOW search_term - ILIKE is fine
GET /v1/transcripts/search?q=machine+learning&page=1 - BUT KEEP FILTERS like in /transcripts

```

#### Response
Enhanced response with search metadata:
```json
{
  "items": [
    {
      "id": "abc123",
      "title": "AI Strategy Meeting",
      "created_at": "2024-01-15T10:00:00Z",
      "duration": 3600,
      "status": "ended",
      
      // New search-specific field
      "search_snippet": ["discussed machine learning applications in customer service"], # TODO RETHINK 0 maybe backend maybe front
      
      // Existing fields
      "short_summary": "Team alignment on AI initiatives",
      "long_summary": "Detailed discussion about machine learning...",
      ...
    }
  ],
  "total": 42,
  "page": 1,
  "pages": 5
}
```

### 4. Search Implementation

#### Why Backend Generates Snippets

Snippet generation must happen on the backend because:

1. **Data Access**: Frontend only receives minimal transcript data in list views. Full transcript text lives in `topics[].transcript` which isn't sent in search results to avoid massive payloads.

2. **Performance**: Sending full transcript content for each search result would create huge response sizes (potentially MBs per request), especially with multiple results.

3. **Efficiency**: Backend already has the data in memory after PostgreSQL returns results. Extracting snippets server-side avoids duplicate work.

4. **Network Optimization**: Sending only 150-character snippets instead of full transcripts reduces bandwidth by 100x or more.

```python
# transcripts_controller.py
async def get_all(self, search_term: str | None = None, ...):
    if search_term:
        if database.url.dialect != "postgresql":
            logger.warning("Search functionality requires PostgreSQL. Returning empty results.")
            return []
        
        # Full-text search with ranking
        search_query = sa.select([
            transcripts,
            sa.func.ts_rank(transcripts.c.search_vector, 
                           sa.func.plainto_tsquery('english', search_term)).label('rank')
        ]).where(
            transcripts.c.search_vector.match(search_term)
        ).order_by(
            sa.desc('rank')
        )
        
        results = await database.fetch_all(search_query)
        
        # Post-process to add search snippet
        for result in results:
            # Generate search snippet from best match
            snippet = self._generate_search_snippet(result, search_term)
            result['search_snippet'] = snippet
        
        return results

def _generate_search_snippet(self, transcript, search_term):
    """Generate snippet from best match"""
    search_lower = search_term.lower()
    
    # Priority 1: Check title
    if transcript.title and search_lower in transcript.title.lower():
        return self._highlight_text(transcript.title, search_term)
    
    # Priority 2: Check short summary
    if transcript.short_summary and search_lower in transcript.short_summary.lower():
        return self._highlight_text(transcript.short_summary[:150], search_term)
    
    # Priority 3: Check long summary
    if transcript.long_summary and search_lower in transcript.long_summary.lower():
        return self._highlight_text(transcript.long_summary[:150], search_term)
    
    # Priority 4: Check transcript content
    for topic in transcript.topics:
        if topic.get('transcript') and search_lower in topic['transcript'].lower():
            text = topic['transcript']
            match_pos = text.lower().find(search_lower)
            start = max(0, match_pos - 50)
            end = min(len(text), match_pos + 100)
            snippet = text[start:end]
            return self._highlight_text(snippet, search_term)
    
    # Shouldn't happen if PostgreSQL FTS found a match
    return ""
```

### 5. User Interface Changes

#### Search Results View

TODO iterate UIs - iterate interface on N matches inside 1 doc
TODO try other similar tools (Loom, etc)
TODO apps like reflector topic in zulip

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search: "machine learning"            3 results found     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ AI Strategy Meeting              Jan 15, 2024 • 1h    │    │
│ │                                                       │    │
│ │ discussed **machine learning** applications in       │    │
│ │ customer service and fraud detection                 │    │
│ │                                                       │    │
│ │                                              [View →] │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ **Machine Learning** Workshop    Jan 10, 2024 • 2h   │    │
│ │                                                       │    │
│ │ **Machine Learning** Workshop                        │    │
│ │                                                       │    │
│ │                                              [View →] │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Empty State (SQLite or when postgre has no results)
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search: "machine learning"                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Search requires PostgreSQL database.                       │
│   Please check with your administrator.                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6. Technical Requirements

#### Performance
- Search response time < 500ms for up to 10k transcripts
- Snippet generation should not block results
- Results paginated (20 per page)

#### Migration
- Backward compatible - no breaking changes
- One-time migration to add search_vector and populate existing data
- Automatic updates via trigger for new/updated transcripts

#### Developer Experience
- Clear documentation on PostgreSQL requirement
- Log messages guide developers to use PostgreSQL
- No code changes needed for non-search features

## Implementation Plan

### Phase 1: MVP (2 weeks)
1. Database migration for search_vector with transcript content extraction
2. Update transcripts_controller with FTS queries and snippet generation
3. Add search_snippet and matched_fields to API response
4. Update frontend to display enhanced results with match indicators
5. Documentation updates for PostgreSQL requirement

### Phase 2: Enhancements (Future)
1. Advanced search syntax (field:value, phrases with quotes)
2. Search filters (date range, duration, speaker)
3. Search suggestions/autocomplete
4. Performance optimizations for large datasets
5. Search analytics and popular terms

## Success Metrics

1. **Search Usage**: 50% of active users use search weekly
2. **Search Success Rate**: 80% of searches result in clicked results
3. **Time to Find**: Average time to find target transcript reduced by 60%
4. **User Feedback**: Positive feedback on search effectiveness

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PostgreSQL-only feature confuses SQLite users | Medium | Clear warning messages and documentation |
| Performance degradation with large datasets | High | GIN indexes and query optimization |
| Search quality issues | Medium | Weighted search (A-D) and continuous tuning |
| Snippet generation from JSON is slow | Medium | Application-level caching and optimization |
| Transcript content increases index size | Low | Monitor storage, optimize trigger function |

## Open Questions

1. Should we support phrase search ("exact phrase") in MVP?
2. How many characters should snippets show? (Proposed: 150)
3. Should we highlight all occurrences or just the first?
4. Do we need search analytics in the future?
5. Should we show which topic within a transcript matched?
6. How to handle very long transcripts with many matches?

## Appendix: Example Queries

### Basic Search
```sql
-- Find transcripts mentioning "budget"
SELECT * FROM transcript
WHERE search_vector @@ plainto_tsquery('english', 'budget')
ORDER BY ts_rank(search_vector, plainto_tsquery('english', 'budget')) DESC;
```

### Multi-word Search
```sql
-- Find transcripts with "machine learning"
SELECT * FROM transcript
WHERE search_vector @@ plainto_tsquery('english', 'machine learning')
ORDER BY ts_rank(search_vector, plainto_tsquery('english', 'machine learning')) DESC;
```

### Future: Phrase Search
```sql
-- Find exact phrase "quarterly review"
SELECT * FROM transcript
WHERE search_vector @@ phraseto_tsquery('english', 'quarterly review')
ORDER BY ts_rank(search_vector, phraseto_tsquery('english', 'quarterly review')) DESC;
```