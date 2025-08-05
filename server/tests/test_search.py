import pytest
from reflector.utils.snippet import highlight_text, generate_snippet
from reflector.db.search import build_search_query
from sqlalchemy import select, table, column


class TestSnippetGeneration:
    """Test the pure snippet generation functions"""
    
    def test_highlight_text_simple(self):
        assert highlight_text("Hello world", "world") == "Hello **world**"
        
    def test_highlight_text_case_insensitive(self):
        assert highlight_text("Hello WORLD", "world") == "Hello **WORLD**"
        assert highlight_text("hello world", "WORLD") == "hello **world**"
        
    def test_highlight_text_multiple_occurrences(self):
        text = "The world is round. The world spins."
        expected = "The **world** is round. The **world** spins."
        assert highlight_text(text, "world") == expected
        
    def test_highlight_text_special_chars(self):
        # Test that special regex chars are escaped
        assert highlight_text("Cost is $500", "$500") == "Cost is **$500**"
        assert highlight_text("Use [brackets]", "[brackets]") == "Use **[brackets]**"
        
    def test_generate_snippet_from_title(self):
        transcript = {
            "title": "Budget Meeting Q4 2024",
            "short_summary": "Also mentions budget",
            "long_summary": "Budget is discussed in detail"
        }
        # Title has highest priority
        assert generate_snippet(transcript, "budget") == "**Budget** Meeting Q4 2024"
        
    def test_generate_snippet_from_short_summary(self):
        transcript = {
            "title": "Team Meeting",
            "short_summary": "Discussion about budget allocation for next quarter"
        }
        snippet = generate_snippet(transcript, "budget")
        assert "**budget**" in snippet
        assert "allocation" in snippet
        
    def test_generate_snippet_from_long_summary(self):
        transcript = {
            "title": "Meeting",
            "short_summary": "Team sync",
            "long_summary": "We covered many topics including the budget planning for Q4 and resource allocation"
        }
        snippet = generate_snippet(transcript, "budget")
        assert "**budget**" in snippet
        assert len(snippet) <= 150  # Check max length
        
    def test_generate_snippet_from_topics(self):
        transcript = {
            "title": "Meeting",
            "topics": [
                {"transcript": "First topic about something else"},
                {"transcript": "Second topic discusses the budget in detail with numbers"},
                {"transcript": "Third topic"}
            ]
        }
        snippet = generate_snippet(transcript, "budget")
        assert "**budget**" in snippet
        assert "Second topic" in snippet
        
    def test_generate_snippet_context_extraction(self):
        # Test that we get context around the match
        long_text = "a" * 50 + " budget planning " + "b" * 50
        transcript = {"long_summary": long_text}
        snippet = generate_snippet(transcript, "budget")
        
        # Should include some context before and after
        assert "aaa" in snippet
        assert "bbb" in snippet
        assert "**budget**" in snippet
        assert len(snippet) <= 150
        
    def test_generate_snippet_no_match(self):
        transcript = {
            "title": "Meeting",
            "short_summary": "Team sync",
            "topics": [{"transcript": "Nothing relevant"}]
        }
        assert generate_snippet(transcript, "budget") == ""
        
    def test_generate_snippet_empty_transcript(self):
        assert generate_snippet({}, "budget") == ""
        assert generate_snippet({"title": None}, "budget") == ""


class TestSearchQuery:
    """Test the database-agnostic search query builder"""
    
    def test_postgresql_query(self):
        # Create a mock table structure
        transcripts = table('transcript',
            column('id'),
            column('title'),
            column('search_vector')
        )
        base = select(transcripts)
        
        query = build_search_query(base, "test search", "postgresql")
        assert query is not None
        
        # Convert to string to check SQL
        query_str = str(query.compile())
        assert "search_vector @@" in query_str
        assert "plainto_tsquery" in query_str
        assert "ts_rank" in query_str
        
    def test_sqlite_returns_none(self):
        transcripts = table('transcript')
        base = select(transcripts)
        
        query = build_search_query(base, "test", "sqlite")
        assert query is None
        
    def test_mysql_returns_none(self):
        transcripts = table('transcript')
        base = select(transcripts)
        
        query = build_search_query(base, "test", "mysql")
        assert query is None


class TestFactories:
    """Test data generation helpers"""
    
    def test_make_transcript(self):
        from tests.factories import make_transcript
        
        # Test defaults
        transcript = make_transcript()
        assert transcript["title"] == "Test Transcript"
        assert transcript["status"] == "complete"
        assert "id" in transcript
        assert "created_at" in transcript
        
        # Test overrides
        custom = make_transcript(
            title="Custom Title",
            short_summary="Custom summary"
        )
        assert custom["title"] == "Custom Title"
        assert custom["short_summary"] == "Custom summary"
        assert custom["status"] == "complete"  # default preserved
        
    def test_make_transcript_with_search_data(self):
        from tests.factories import make_transcript
        
        # Create test data for search scenarios
        transcript = make_transcript(
            title="Budget Review Meeting",
            short_summary="Q4 budget discussion",
            long_summary="Detailed review of Q4 budget allocations and spending",
            topics=[
                {
                    "title": "Opening remarks",
                    "transcript": "Welcome everyone to the budget review"
                },
                {
                    "title": "Budget details", 
                    "transcript": "Our Q4 budget is $2.5M with allocations across departments"
                }
            ]
        )
        
        # This data can be used directly in tests
        snippet = generate_snippet(transcript, "budget")
        assert "**Budget**" in snippet


# Integration test example (marked for real PostgreSQL)
@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_search_integration(postgresql_db):
    """Test with real PostgreSQL database"""
    from reflector.db.transcripts import TranscriptController
    from reflector.models.transcript import Transcript
    
    controller = TranscriptController()
    
    # Create test transcripts
    transcripts_data = [
        {
            "title": "Budget Planning Meeting",
            "short_summary": "Q4 budget review",
            "long_summary": "Comprehensive budget planning for Q4 2024"
        },
        {
            "title": "Team Standup",
            "short_summary": "Daily sync",
            "long_summary": "Quick team synchronization meeting"
        },
        {
            "title": "Technical Review",
            "short_summary": "Code review session",
            "long_summary": "Review of new features with budget impact analysis"
        }
    ]
    
    created_ids = []
    for data in transcripts_data:
        transcript = Transcript(**data)
        created = await controller.create(transcript)
        created_ids.append(created.id)
    
    # Search for budget
    results = await controller.get_all(search_term="budget")
    
    # Should find 2 results
    assert len(results) == 2
    
    # Check ordering - exact title match should be first
    assert results[0]['title'] == "Budget Planning Meeting"
    assert results[1]['title'] == "Technical Review"
    
    # Check snippets
    assert results[0]['search_snippet'] == "**Budget** Planning Meeting"
    assert "**budget**" in results[1]['search_snippet']
    
    # Cleanup
    for tid in created_ids:
        await controller.delete(tid)