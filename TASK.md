# Full-Text Search Implementation Task

## Overview
Implement PostgreSQL full-text search for the transcripts table using `title` and `vtt` fields with automatic index maintenance via generated columns.

## Database Changes

### 1. Add Search Vector Column
```sql
ALTER TABLE transcript ADD COLUMN search_vector_en tsvector 
GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(webvtt, '')), 'B')
) STORED;

CREATE INDEX idx_transcript_search_vector_en ON transcript USING GIN(search_vector_en);
```

### 2. Migration File
Create `migrations/versions/xxx_add_full_text_search.py`:
```python
def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return  # Skip for SQLite
    
    op.execute("""
        ALTER TABLE transcript ADD COLUMN search_vector_en tsvector 
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(webvtt, '')), 'B')
        ) STORED
    """)
    
    op.create_index(
        'idx_transcript_search_vector_en',
        'transcript',
        ['search_vector_en'],
        postgresql_using='gin'
    )

def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return
    
    op.drop_index('idx_transcript_search_vector_en')
    op.drop_column('transcript', 'search_vector_en')
```

## Code Implementation

### 1. Database Detection Utility
Add to `reflector/db/utils.py`:
```python
from reflector.settings import settings

def is_postgresql() -> bool:
    """Check if using PostgreSQL database."""
    return "postgresql" in settings.DATABASE_URL.lower()
```

### 2. Search Methods
Add to `reflector/db/transcripts.py` in `TranscriptController`:
```python
async def search_full_text(
    self,
    query_text: str,
    user_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    source_kind: SourceKind | None = None,
    room_id: str | None = None,
) -> tuple[list[dict], int]:
    """
    Full-text search using PostgreSQL tsvector.
    Returns (results, total_count).
    """
    from reflector.db.utils import is_postgresql
    
    if not is_postgresql():
        logger.warning(
            "Full-text search requires PostgreSQL. Returning empty results."
        )
        return [], 0
    
    # Use websearch_to_tsquery for flexible user input
    search_query = sa.func.websearch_to_tsquery('english', query_text)
    
    # Build search query with ranking
    base_query = (
        sa.select([
            transcripts.c.id,
            transcripts.c.title,
            transcripts.c.created_at,
            transcripts.c.duration,
            transcripts.c.status,
            transcripts.c.user_id,
            transcripts.c.room_id,
            transcripts.c.source_kind,
            sa.func.ts_rank(
                transcripts.c.search_vector_en,
                search_query,
                32  # normalization: rank/(rank+1) for 0-1 range
            ).label('rank')
        ])
        .where(transcripts.c.search_vector_en.op('@@')(search_query))
    )
    
    # Apply filters
    if user_id:
        base_query = base_query.where(transcripts.c.user_id == user_id)
    if source_kind:
        base_query = base_query.where(transcripts.c.source_kind == source_kind)
    if room_id:
        base_query = base_query.where(transcripts.c.room_id == room_id)
    
    # Get paginated results
    query = base_query.order_by(sa.desc('rank')).limit(limit).offset(offset)
    results = await database.fetch_all(query)
    
    # Get total count
    count_query = sa.select([sa.func.count()]).select_from(
        base_query.alias('search_results')
    )
    total = await database.fetch_val(count_query)
    
    return [dict(r) for r in results], total
```


## Testing

**IMPORTANT NOTE**: Tests currently use SQLite (in-memory) for speed and isolation. PostgreSQL-specific features like full-text search cannot be tested in the current test suite. The tests below skip PostgreSQL-only features when running on SQLite.

Create `tests/test_search.py`:
```python
import pytest
from reflector.db.utils import is_postgresql

@pytest.mark.skipif(not is_postgresql(), reason="PostgreSQL only")
class TestFullTextSearch:
    async def test_basic_search(self, db_session, transcript_factory):
        # Create test data
        t1 = await transcript_factory(
            title="Machine Learning Workshop",
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker0>Welcome to our machine learning workshop"
        )
        t2 = await transcript_factory(
            title="Quarterly Review",
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker0>Let's review the quarterly results"
        )
        
        # Search for "machine learning"
        results, total = await transcripts_controller.search_full_text(
            "machine learning"
        )
        
        assert total == 1
        assert results[0]['id'] == t1.id
        assert results[0]['rank'] > 0
    
    async def test_websearch_syntax(self, db_session, transcript_factory):
        t1 = await transcript_factory(title="Python Programming")
        t2 = await transcript_factory(title="Python and JavaScript")
        
        # Test OR syntax
        results, total = await transcripts_controller.search_full_text(
            "Python OR JavaScript"
        )
        assert total == 2
        
        # Test exclusion
        results, total = await transcripts_controller.search_full_text(
            "Python -JavaScript"
        )
        assert total == 1
        assert results[0]['id'] == t1.id
    
    async def test_ranking(self, db_session, transcript_factory):
        # Title match should rank higher
        t1 = await transcript_factory(
            title="Machine Learning",
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker0>Some other content"
        )
        t2 = await transcript_factory(
            title="Other Topic",
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v Speaker0>Discussing machine learning"
        )
        
        results, _ = await transcripts_controller.search_full_text(
            "machine learning"
        )
        
        # Title match (weight A) should rank higher than content (weight B)
        assert results[0]['id'] == t1.id
        assert results[0]['rank'] > results[1]['rank']

@pytest.mark.skipif(is_postgresql(), reason="SQLite fallback test")
async def test_sqlite_fallback(db_session):
    results, total = await transcripts_controller.search_full_text(
        "any query"
    )
    assert results == []
    assert total == 0
```


## Implementation Checklist

- [ ] Create database migration
- [ ] Add `is_postgresql()` utility
- [ ] Implement `search_full_text()` method
- [ ] Write comprehensive tests
- [ ] Document SQLite limitations

## Notes

- WebVTT format includes timestamps and speaker tags that will be indexed. This is acceptable noise for the benefit of automatic maintenance.
- The generated column approach ensures consistency and requires no application-level maintenance.
- Weight A (title) > Weight B (content) ensures title matches rank higher.
- Using `websearch_to_tsquery` allows users to use intuitive search syntax (quotes, OR, -).
- No ts_headline implementation initially - can be added later if needed.
- **Development uses PostgreSQL via Docker Compose** (configured in `.env` with `DATABASE_URL=postgresql://reflector:reflector@postgres:5432/reflector`)
- **Tests still use SQLite** - PostgreSQL-specific features must be tested manually or skipped in automated tests