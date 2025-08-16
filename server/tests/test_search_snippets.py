"""Unit tests for search snippet generation."""

from reflector.db.search import (
    SearchController,
    SnippetCandidate,
    combine_snippet_sources,
    create_snippet,
    extract_webvtt_text,
    filter_non_overlapping_snippets,
    find_all_matches,
    generate_snippets,
    generate_summary_snippets,
    generate_webvtt_snippets,
)


class TestExtractWebVTT:
    """Test WebVTT text extraction."""

    def test_extract_webvtt_with_speakers(self):
        """Test extraction removes speaker tags and timestamps."""
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:10.000
<v Speaker0>Hello world, this is a test.

00:00:10.000 --> 00:00:20.000
<v Speaker1>Indeed it is a test of WebVTT parsing.
"""
        result = SearchController._extract_webvtt_text(webvtt)
        assert "Hello world, this is a test" in result
        assert "Indeed it is a test" in result
        assert "<v Speaker" not in result
        assert "00:00" not in result
        assert "-->" not in result

    def test_extract_empty_webvtt(self):
        """Test empty WebVTT returns empty string."""
        assert SearchController._extract_webvtt_text("") == ""
        assert SearchController._extract_webvtt_text(None) == ""

    def test_extract_malformed_webvtt(self):
        """Test malformed WebVTT returns empty string."""
        result = SearchController._extract_webvtt_text("Not a valid WebVTT")
        assert result == ""


class TestGenerateSnippets:
    """Test snippet generation from plain text."""

    def test_multiple_matches(self):
        """Test finding multiple occurrences of search term in long text."""
        # Create text with Python mentions far apart to get separate snippets
        separator = " This is filler text. " * 20  # ~400 chars of padding
        text = (
            "Python is great for machine learning."
            + separator
            + "Many companies use Python for data science."
            + separator
            + "Python has excellent libraries for analysis."
            + separator
            + "The Python community is very supportive."
        )

        snippets = SearchController._generate_snippets(text, "Python")
        # With enough separation, we should get multiple snippets
        assert len(snippets) >= 2  # At least 2 distinct snippets

        # Each snippet should contain "Python"
        for snippet in snippets:
            assert "python" in snippet.lower()

    def test_single_match(self):
        """Test single occurrence returns one snippet."""
        text = "This document discusses artificial intelligence and its applications."
        snippets = SearchController._generate_snippets(text, "artificial intelligence")

        assert len(snippets) == 1
        assert "artificial intelligence" in snippets[0].lower()

    def test_no_matches(self):
        """Test no matches returns empty list."""
        text = "This is some random text without the search term."
        snippets = SearchController._generate_snippets(text, "machine learning")

        assert snippets == []

    def test_case_insensitive_search(self):
        """Test search is case insensitive."""
        # Add enough text between matches to get separate snippets
        text = (
            "MACHINE LEARNING is important for modern applications. "
            + "It requires lots of data and computational resources. " * 5  # Padding
            + "Machine Learning rocks and transforms industries. "
            + "Deep learning is a subset of it. " * 5  # More padding
            + "Finally, machine learning will shape our future."
        )

        snippets = SearchController._generate_snippets(text, "machine learning")

        # Should find at least 2 (might be 3 if text is long enough)
        assert len(snippets) >= 2
        for snippet in snippets:
            assert "machine learning" in snippet.lower()

    def test_partial_match_fallback(self):
        """Test fallback to first word when exact phrase not found."""
        text = "We use machine intelligence for processing."
        snippets = SearchController._generate_snippets(text, "machine learning")

        # Should fall back to finding "machine"
        assert len(snippets) == 1
        assert "machine" in snippets[0].lower()

    def test_snippet_ellipsis(self):
        """Test ellipsis added for truncated snippets."""
        # Long text where match is in the middle
        text = "a " * 100 + "TARGET_WORD special content here" + " b" * 100
        snippets = SearchController._generate_snippets(text, "TARGET_WORD")

        assert len(snippets) == 1
        assert "..." in snippets[0]  # Should have ellipsis
        assert "TARGET_WORD" in snippets[0]

    def test_overlapping_snippets_deduplicated(self):
        """Test overlapping matches don't create duplicate snippets."""
        text = "test test test word" * 10  # Repeated pattern
        snippets = SearchController._generate_snippets(text, "test")

        # Should get unique snippets, not duplicates
        assert len(snippets) <= 3
        assert len(snippets) == len(set(snippets))  # All unique

    def test_empty_inputs(self):
        """Test empty text or search term returns empty list."""
        assert SearchController._generate_snippets("", "search") == []
        assert SearchController._generate_snippets("text", "") == []
        assert SearchController._generate_snippets("", "") == []

    def test_max_snippets_limit(self):
        """Test respects max_snippets parameter."""
        # Create text with well-separated occurrences
        separator = " filler " * 50  # Ensure snippets don't overlap
        text = ("Python is amazing" + separator) * 10  # 10 occurrences

        # Test with different limits
        snippets_1 = SearchController._generate_snippets(text, "Python", max_snippets=1)
        assert len(snippets_1) == 1

        snippets_2 = SearchController._generate_snippets(text, "Python", max_snippets=2)
        assert len(snippets_2) == 2

        snippets_5 = SearchController._generate_snippets(text, "Python", max_snippets=5)
        assert len(snippets_5) == 5  # Should get exactly 5 with enough separation

    def test_snippet_length(self):
        """Test snippet length is reasonable."""
        text = "word " * 200  # Long text
        snippets = SearchController._generate_snippets(text, "word")

        for snippet in snippets:
            # Default max_length is 150 + some context
            assert len(snippet) <= 200  # Some buffer for ellipsis


class TestFullPipeline:
    """Test the complete WebVTT to snippets pipeline."""

    def test_webvtt_to_snippets_integration(self):
        """Test full pipeline from WebVTT to search snippets."""
        # Create WebVTT with well-separated content for multiple snippets
        webvtt = (
            """WEBVTT

00:00:00.000 --> 00:00:10.000
<v Speaker0>Let's discuss machine learning applications in modern technology.

00:00:10.000 --> 00:00:20.000
<v Speaker1>"""
            + "Various industries are adopting new technologies. " * 10
            + """

00:00:20.000 --> 00:00:30.000
<v Speaker2>Machine learning is revolutionizing healthcare and diagnostics.

00:00:30.000 --> 00:00:40.000
<v Speaker3>"""
            + "Financial markets show interesting patterns. " * 10
            + """

00:00:40.000 --> 00:00:50.000
<v Speaker0>Machine learning in education provides personalized experiences.
"""
        )

        # Extract and generate snippets
        plain_text = SearchController._extract_webvtt_text(webvtt)
        snippets = SearchController._generate_snippets(plain_text, "machine learning")

        # Should find at least 2 snippets (text might still be close together)
        assert len(snippets) >= 1  # At minimum one snippet containing matches
        assert len(snippets) <= 3  # At most 3 by default

        # No WebVTT artifacts in snippets
        for snippet in snippets:
            assert "machine learning" in snippet.lower()
            assert "<v Speaker" not in snippet
            assert "00:00" not in snippet
            assert "-->" not in snippet


# Additional tests merged from test_search_enhancements.py


class TestSnippetGenerationEnhanced:
    """Additional snippet generation tests from test_search_enhancements.py."""

    def test_snippet_generation_from_webvtt(self):
        """Test snippet generation from WebVTT content."""
        controller = SearchController()
        webvtt_content = """WEBVTT

00:00:00.000 --> 00:00:05.000
This is the beginning of the transcript

00:00:05.000 --> 00:00:10.000
The search term appears here in the middle

00:00:10.000 --> 00:00:15.000
And this is the end of the content"""

        plain_text = controller._extract_webvtt_text(webvtt_content)
        snippets = controller._generate_snippets(plain_text, "search term")

        assert len(snippets) > 0
        assert any("search term" in snippet.lower() for snippet in snippets)

    def test_extract_webvtt_text_with_malformed_variations(self):
        """Test WebVTT extraction with various malformed content."""
        controller = SearchController()

        # Test with completely invalid content
        malformed_vtt = "This is not valid WebVTT content"
        result = controller._extract_webvtt_text(malformed_vtt)
        assert result == ""

        # Test with partial WebVTT header
        partial_vtt = "WEBVTT\nNo timestamps here"
        result = controller._extract_webvtt_text(partial_vtt)
        # Should still fail since no valid cues
        assert result == "" or "No timestamps" not in result


class TestPureFunctions:
    """Test the pure functions extracted for functional programming."""

    def test_find_all_matches(self):
        """Test finding all match positions in text."""
        text = "Python is great. Python is powerful. I love Python."
        matches = list(find_all_matches(text, "Python"))
        assert matches == [0, 17, 44]

        # Test case insensitive matching
        matches = list(find_all_matches(text, "python"))
        assert matches == [0, 17, 44]

        # Test no matches
        matches = list(find_all_matches(text, "Ruby"))
        assert matches == []

        # Test empty inputs
        matches = list(find_all_matches("", "test"))
        assert matches == []
        matches = list(find_all_matches("test", ""))
        assert matches == []

    def test_create_snippet(self):
        """Test creating a snippet from a match position."""
        text = "This is a long text with the word Python in the middle and more text after."

        # Test basic snippet creation
        snippet = create_snippet(text, 35, max_length=150)
        assert "Python" in snippet.text
        assert snippet.start >= 0
        assert snippet.end <= len(text)
        assert isinstance(snippet, SnippetCandidate)

        # Test snippet properties are valid
        assert len(snippet.text) > 0
        assert snippet.start <= snippet.end

        # Test with a position that would require ellipsis
        long_text = "A" * 200  # Very long text
        snippet = create_snippet(long_text, 100, max_length=50)
        assert snippet.text.startswith("...")
        assert snippet.text.endswith("...")

        # Test basic bounds checking
        snippet = create_snippet("short text", 0, max_length=100)
        assert snippet.start == 0
        assert "short text" in snippet.text

    def test_filter_non_overlapping_snippets(self):
        """Test filtering overlapping snippets."""
        # Create some snippet candidates
        candidates = [
            SnippetCandidate("First snippet", 0, 20),
            SnippetCandidate("Overlapping", 15, 35),  # Overlaps with first
            SnippetCandidate("Third snippet", 40, 60),  # Non-overlapping
            SnippetCandidate("Fourth snippet", 65, 85),  # Non-overlapping
        ]

        filtered = list(filter_non_overlapping_snippets(iter(candidates)))
        assert filtered == ["First snippet", "Third snippet", "Fourth snippet"]

        # Test with no candidates
        filtered = list(filter_non_overlapping_snippets(iter([])))
        assert filtered == []

    def test_generate_snippets_integration(self):
        """Test the main generate_snippets function."""
        text = "Machine learning is amazing. Machine learning transforms data. Learn machine learning today."

        # Test basic snippet generation
        snippets = generate_snippets(text, "machine learning")
        assert len(snippets) <= 3  # Default max
        assert all("machine learning" in s.lower() for s in snippets)

        # Test max snippets limit
        snippets = generate_snippets(text, "machine learning", max_snippets=2)
        assert len(snippets) <= 2

        # Test fallback to first word
        snippets = generate_snippets(text, "machine vision")  # "vision" not found
        assert len(snippets) > 0  # Should find "machine"
        assert any("machine" in s.lower() for s in snippets)

    def test_extract_webvtt_text_basic(self):
        """Test WebVTT text extraction (basic test, full tests exist elsewhere)."""
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
This is a test"""

        result = extract_webvtt_text(webvtt)
        assert "Hello world" in result
        assert "This is a test" in result

        # Test empty input
        assert extract_webvtt_text("") == ""
        assert extract_webvtt_text(None) == ""

    def test_generate_webvtt_snippets(self):
        """Test generating snippets from WebVTT content."""
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Python programming is great

00:00:02.000 --> 00:00:04.000
Learn Python today"""

        snippets = generate_webvtt_snippets(webvtt, "Python")
        assert len(snippets) > 0
        assert any("Python" in s for s in snippets)

        # Test empty WebVTT
        snippets = generate_webvtt_snippets("", "Python")
        assert snippets == []

    def test_generate_summary_snippets(self):
        """Test generating snippets from summary text."""
        summary = "This meeting discussed Python development and machine learning applications."

        snippets = generate_summary_snippets(summary, "Python")
        assert len(snippets) > 0
        assert any("Python" in s for s in snippets)

        # Test with max limit (should use LONG_SUMMARY_MAX_SNIPPETS)
        long_summary = "Python " * 20  # Many occurrences
        snippets = generate_summary_snippets(long_summary, "Python")
        assert len(snippets) <= 2  # LONG_SUMMARY_MAX_SNIPPETS

    def test_combine_snippet_sources(self):
        """Test combining snippets from multiple sources."""
        summary = "Python is a great programming language."
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Learn Python programming

00:00:02.000 --> 00:00:04.000
Python is powerful"""

        # Test combining both sources
        snippets, total_count = combine_snippet_sources(
            summary, webvtt, "Python", max_total=3
        )
        assert len(snippets) <= 3
        assert len(snippets) > 0
        assert total_count > 0

        # Test summary-only
        snippets, total_count = combine_snippet_sources(
            summary, None, "Python", max_total=3
        )
        assert len(snippets) > 0
        assert all("Python" in s for s in snippets)
        assert total_count == 1  # "Python" appears once in summary

        # Test webvtt-only
        snippets, total_count = combine_snippet_sources(
            None, webvtt, "Python", max_total=3
        )
        assert len(snippets) > 0
        assert total_count == 2  # "Python" appears twice in webvtt

        # Test priority (summary first)
        long_summary = "Python " * 10  # Should fill quota from summary
        snippets, total_count = combine_snippet_sources(
            long_summary, webvtt, "Python", max_total=2
        )
        assert len(snippets) == 2  # Should be filled from summary
        assert total_count >= 10  # At least 10 from summary

    def test_match_counting_sum_logic(self):
        """Test that match counting correctly sums matches from both sources."""
        # Create content with known match counts
        summary = (
            "data science uses data analysis and data mining techniques"  # 3 matches
        )
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Big data processing

00:00:02.000 --> 00:00:04.000
data visualization and data storage"""  # 3 matches

        # Test that matches are summed correctly
        snippets, total_count = combine_snippet_sources(
            summary, webvtt, "data", max_total=3
        )
        assert total_count == 6  # 3 (summary) + 3 (webvtt) = 6
        assert len(snippets) <= 3  # Snippets should still be limited

        # Test individual sources for verification
        summary_snippets, summary_count = combine_snippet_sources(
            summary, None, "data", max_total=3
        )
        assert summary_count == 3

        webvtt_snippets, webvtt_count = combine_snippet_sources(
            None, webvtt, "data", max_total=3
        )
        assert webvtt_count == 3

        # Test empty/None sources
        snippets_empty, count_empty = combine_snippet_sources(
            None, None, "data", max_total=3
        )
        assert snippets_empty == []
        assert count_empty == 0

    def test_edge_cases(self):
        """Test edge cases for the pure functions."""
        # Test with special characters
        text = "Test with special: @#$%^&*() characters"
        snippets = generate_snippets(text, "@#$%")
        assert len(snippets) > 0

        # Test with very long query
        long_query = "a" * 100
        snippets = generate_snippets("Some text", long_query)
        assert snippets == []  # No match

        # Test with unicode
        text = "Unicode test: café, naïve, 日本語"
        snippets = generate_snippets(text, "café")
        assert len(snippets) > 0
        assert "café" in snippets[0]
