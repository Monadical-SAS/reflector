"""Unit tests for search snippet generation."""

import pytest

from reflector.db.search import (
    SnippetCandidate,
    SnippetGenerator,
    WebVTTProcessor,
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
        result = WebVTTProcessor.extract_text(webvtt)
        assert "Hello world, this is a test" in result
        assert "Indeed it is a test" in result
        assert "<v Speaker" not in result
        assert "00:00" not in result
        assert "-->" not in result

    def test_extract_empty_webvtt(self):
        """Test empty WebVTT returns empty string."""
        assert WebVTTProcessor.extract_text("") == ""

    def test_extract_malformed_webvtt(self):
        """Test malformed WebVTT returns empty string."""
        result = WebVTTProcessor.extract_text("Not a valid WebVTT")
        assert result == ""


class TestGenerateSnippets:
    """Test snippet generation from plain text."""

    def test_multiple_matches(self):
        """Test finding multiple occurrences of search term in long text."""
        separator = " This is filler text. " * 20
        text = (
            "Python is great for machine learning."
            + separator
            + "Many companies use Python for data science."
            + separator
            + "Python has excellent libraries for analysis."
            + separator
            + "The Python community is very supportive."
        )

        snippets = SnippetGenerator.generate(text, "Python")
        assert len(snippets) >= 2

        for snippet in snippets:
            assert "python" in snippet.lower()

    def test_single_match(self):
        """Test single occurrence returns one snippet."""
        text = "This document discusses artificial intelligence and its applications."
        snippets = SnippetGenerator.generate(text, "artificial intelligence")

        assert len(snippets) == 1
        assert "artificial intelligence" in snippets[0].lower()

    def test_no_matches(self):
        """Test no matches returns empty list."""
        text = "This is some random text without the search term."
        snippets = SnippetGenerator.generate(text, "machine learning")

        assert snippets == []

    def test_case_insensitive_search(self):
        """Test search is case insensitive."""
        text = (
            "MACHINE LEARNING is important for modern applications. "
            + "It requires lots of data and computational resources. " * 5
            + "Machine Learning rocks and transforms industries. "
            + "Deep learning is a subset of it. " * 5
            + "Finally, machine learning will shape our future."
        )

        snippets = SnippetGenerator.generate(text, "machine learning")

        assert len(snippets) >= 2
        for snippet in snippets:
            assert "machine learning" in snippet.lower()

    def test_partial_match_fallback(self):
        """Test fallback to first word when exact phrase not found."""
        text = "We use machine intelligence for processing."
        snippets = SnippetGenerator.generate(text, "machine learning")

        assert len(snippets) == 1
        assert "machine" in snippets[0].lower()

    def test_snippet_ellipsis(self):
        """Test ellipsis added for truncated snippets."""
        text = "a " * 100 + "TARGET_WORD special content here" + " b" * 100
        snippets = SnippetGenerator.generate(text, "TARGET_WORD")

        assert len(snippets) == 1
        assert "..." in snippets[0]
        assert "TARGET_WORD" in snippets[0]

    def test_overlapping_snippets_deduplicated(self):
        """Test overlapping matches don't create duplicate snippets."""
        text = "test test test word" * 10
        snippets = SnippetGenerator.generate(text, "test")

        assert len(snippets) <= 3
        assert len(snippets) == len(set(snippets))

    def test_empty_inputs(self):
        """Test empty text or search term returns empty list."""
        assert SnippetGenerator.generate("", "search") == []
        assert SnippetGenerator.generate("text", "") == []
        assert SnippetGenerator.generate("", "") == []

    def test_max_snippets_limit(self):
        """Test respects max_snippets parameter."""
        separator = " filler " * 50
        text = ("Python is amazing" + separator) * 10

        snippets_1 = SnippetGenerator.generate(text, "Python", max_snippets=1)
        assert len(snippets_1) == 1

        snippets_2 = SnippetGenerator.generate(text, "Python", max_snippets=2)
        assert len(snippets_2) == 2

        snippets_5 = SnippetGenerator.generate(text, "Python", max_snippets=5)
        assert len(snippets_5) == 5

    def test_snippet_length(self):
        """Test snippet length is reasonable."""
        text = "word " * 200
        snippets = SnippetGenerator.generate(text, "word")

        for snippet in snippets:
            assert len(snippet) <= 200


class TestFullPipeline:
    """Test the complete WebVTT to snippets pipeline."""

    def test_webvtt_to_snippets_integration(self):
        """Test full pipeline from WebVTT to search snippets."""
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

        plain_text = WebVTTProcessor.extract_text(webvtt)
        snippets = SnippetGenerator.generate(plain_text, "machine learning")

        assert len(snippets) >= 1
        assert len(snippets) <= 3

        for snippet in snippets:
            assert "machine learning" in snippet.lower()
            assert "<v Speaker" not in snippet
            assert "00:00" not in snippet
            assert "-->" not in snippet


class TestMultiWordQueryBehavior:
    """Tests for multi-word query behavior and exact phrase matching."""

    def test_multi_word_query_snippet_behavior(self):
        """Test that multi-word queries generate snippets based on exact phrase matching."""
        sample_text = """This is a sample transcript where user Alice is talking.
        Later in the conversation, jordan mentions something important.
        The user jordan collaboration was successful.
        Another user named Bob joins the discussion."""

        user_snippets = SnippetGenerator.generate(sample_text, "user")
        assert len(user_snippets) == 2, "Should find 2 snippets for 'user'"

        jordan_snippets = SnippetGenerator.generate(sample_text, "jordan")
        assert len(jordan_snippets) >= 1, "Should find at least 1 snippet for 'jordan'"

        multi_word_snippets = SnippetGenerator.generate(sample_text, "user jordan")
        assert len(multi_word_snippets) == 1, (
            "Should return exactly 1 snippet for 'user jordan' "
            "(only the exact phrase match, not individual word occurrences)"
        )

        snippet = multi_word_snippets[0]
        assert (
            "user jordan" in snippet.lower()
        ), "The snippet should contain the exact phrase 'user jordan'"

        assert (
            "alice" not in snippet.lower()
        ), "The snippet should not include the first standalone 'user' with Alice"

    def test_multi_word_query_without_exact_match(self):
        """Test snippet generation when exact phrase is not found."""
        sample_text = """User Alice is here. Bob and jordan are talking.
        Later jordan mentions something. The user is happy."""

        snippets = SnippetGenerator.generate(sample_text, "user jordan")

        assert (
            len(snippets) >= 1
        ), "Should find at least 1 snippet when falling back to first word"

        all_snippets_text = " ".join(snippets).lower()
        assert (
            "user" in all_snippets_text
        ), "Snippets should contain 'user' (the first word)"

    def test_exact_phrase_at_text_boundaries(self):
        """Test snippet generation when exact phrase appears at text boundaries."""

        text_start = "user jordan started the meeting. Other content here."
        snippets = SnippetGenerator.generate(text_start, "user jordan")
        assert len(snippets) == 1
        assert "user jordan" in snippets[0].lower()

        text_end = "Other content here. The meeting ended with user jordan"
        snippets = SnippetGenerator.generate(text_end, "user jordan")
        assert len(snippets) == 1
        assert "user jordan" in snippets[0].lower()

    def test_multi_word_query_matches_words_appearing_separately_and_together(self):
        """Test that multi-word queries prioritize exact phrase matches over individual word occurrences."""
        sample_text = """This is a sample transcript where user Alice is talking.
        Later in the conversation, jordan mentions something important.
        The user jordan collaboration was successful.
        Another user named Bob joins the discussion."""

        search_query = "user jordan"
        snippets = SnippetGenerator.generate(sample_text, search_query)

        assert len(snippets) == 1, (
            f"Expected exactly 1 snippet for '{search_query}' when exact phrase exists, "
            f"got {len(snippets)}. Should ignore individual word occurrences."
        )

        snippet = snippets[0]

        assert (
            search_query in snippet.lower()
        ), f"Snippet should contain the exact phrase '{search_query}'. Got: {snippet}"

        assert (
            "jordan mentions" in snippet.lower()
        ), f"Snippet should include context before the exact phrase match. Got: {snippet}"

        assert (
            "alice" not in snippet.lower()
        ), f"Snippet should not include separate occurrences of individual words. Got: {snippet}"

        text_2 = """The alpha version was released.
        Beta testing started yesterday.
        The alpha beta integration is complete."""

        snippets_2 = SnippetGenerator.generate(text_2, "alpha beta")
        assert len(snippets_2) == 1, "Should return 1 snippet for exact phrase match"
        assert "alpha beta" in snippets_2[0].lower(), "Should contain exact phrase"
        assert (
            "version" not in snippets_2[0].lower()
        ), "Should not include first separate occurrence"


class TestSnippetGenerationEnhanced:
    """Additional snippet generation tests from test_search_enhancements.py."""

    def test_snippet_generation_from_webvtt(self):
        """Test snippet generation from WebVTT content."""
        webvtt_content = """WEBVTT

00:00:00.000 --> 00:00:05.000
This is the beginning of the transcript

00:00:05.000 --> 00:00:10.000
The search term appears here in the middle

00:00:10.000 --> 00:00:15.000
And this is the end of the content"""

        plain_text = WebVTTProcessor.extract_text(webvtt_content)
        snippets = SnippetGenerator.generate(plain_text, "search term")

        assert len(snippets) > 0
        assert any("search term" in snippet.lower() for snippet in snippets)

    def test_extract_webvtt_text_with_malformed_variations(self):
        """Test WebVTT extraction with various malformed content."""
        malformed_vtt = "This is not valid WebVTT content"
        result = WebVTTProcessor.extract_text(malformed_vtt)
        assert result == ""

        partial_vtt = "WEBVTT\nNo timestamps here"
        result = WebVTTProcessor.extract_text(partial_vtt)
        assert result == "" or "No timestamps" not in result


class TestPureFunctions:
    """Test the pure functions extracted for functional programming."""

    def test_find_all_matches(self):
        """Test finding all match positions in text."""
        text = "Python is great. Python is powerful. I love Python."
        matches = list(SnippetGenerator.find_all_matches(text, "Python"))
        assert matches == [0, 17, 44]

        matches = list(SnippetGenerator.find_all_matches(text, "python"))
        assert matches == [0, 17, 44]

        matches = list(SnippetGenerator.find_all_matches(text, "Ruby"))
        assert matches == []

        matches = list(SnippetGenerator.find_all_matches("", "test"))
        assert matches == []
        matches = list(SnippetGenerator.find_all_matches("test", ""))
        assert matches == []

    def test_create_snippet(self):
        """Test creating a snippet from a match position."""
        text = "This is a long text with the word Python in the middle and more text after."

        snippet = SnippetGenerator.create_snippet(text, 35, max_length=150)
        assert "Python" in snippet.text()
        assert snippet.start >= 0
        assert snippet.end <= len(text)
        assert isinstance(snippet, SnippetCandidate)

        assert len(snippet.text()) > 0
        assert snippet.start <= snippet.end

        long_text = "A" * 200
        snippet = SnippetGenerator.create_snippet(long_text, 100, max_length=50)
        assert snippet.text().startswith("...")
        assert snippet.text().endswith("...")

        snippet = SnippetGenerator.create_snippet("short text", 0, max_length=100)
        assert snippet.start == 0
        assert "short text" in snippet.text()

    def test_filter_non_overlapping(self):
        """Test filtering overlapping snippets."""
        candidates = [
            SnippetCandidate(_text="First snippet", start=0, _original_text_length=100),
            SnippetCandidate(_text="Overlapping", start=10, _original_text_length=100),
            SnippetCandidate(
                _text="Third snippet", start=40, _original_text_length=100
            ),
            SnippetCandidate(
                _text="Fourth snippet", start=65, _original_text_length=100
            ),
        ]

        filtered = list(SnippetGenerator.filter_non_overlapping(iter(candidates)))
        assert filtered == [
            "First snippet...",
            "...Third snippet...",
            "...Fourth snippet...",
        ]

        filtered = list(SnippetGenerator.filter_non_overlapping(iter([])))
        assert filtered == []

    def test_generate_integration(self):
        """Test the main SnippetGenerator.generate function."""
        text = "Machine learning is amazing. Machine learning transforms data. Learn machine learning today."

        snippets = SnippetGenerator.generate(text, "machine learning")
        assert len(snippets) <= 3
        assert all("machine learning" in s.lower() for s in snippets)

        snippets = SnippetGenerator.generate(text, "machine learning", max_snippets=2)
        assert len(snippets) <= 2

        snippets = SnippetGenerator.generate(text, "machine vision")
        assert len(snippets) > 0
        assert any("machine" in s.lower() for s in snippets)

    def test_extract_webvtt_text_basic(self):
        """Test WebVTT text extraction (basic test, full tests exist elsewhere)."""
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
This is a test"""

        result = WebVTTProcessor.extract_text(webvtt)
        assert "Hello world" in result
        assert "This is a test" in result

        # Test empty input
        assert WebVTTProcessor.extract_text("") == ""
        assert WebVTTProcessor.extract_text(None) == ""

    def test_generate_webvtt_snippets(self):
        """Test generating snippets from WebVTT content."""
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Python programming is great

00:00:02.000 --> 00:00:04.000
Learn Python today"""

        snippets = WebVTTProcessor.generate_snippets(webvtt, "Python")
        assert len(snippets) > 0
        assert any("Python" in s for s in snippets)

        snippets = WebVTTProcessor.generate_snippets("", "Python")
        assert snippets == []

    def test_from_summary(self):
        """Test generating snippets from summary text."""
        summary = "This meeting discussed Python development and machine learning applications."

        snippets = SnippetGenerator.from_summary(summary, "Python")
        assert len(snippets) > 0
        assert any("Python" in s for s in snippets)

        long_summary = "Python " * 20
        snippets = SnippetGenerator.from_summary(long_summary, "Python")
        assert len(snippets) <= 2

    def test_combine_sources(self):
        """Test combining snippets from multiple sources."""
        summary = "Python is a great programming language."
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Learn Python programming

00:00:02.000 --> 00:00:04.000
Python is powerful"""

        snippets, total_count = SnippetGenerator.combine_sources(
            summary, webvtt, "Python", max_total=3
        )
        assert len(snippets) <= 3
        assert len(snippets) > 0
        assert total_count > 0

        snippets, total_count = SnippetGenerator.combine_sources(
            summary, None, "Python", max_total=3
        )
        assert len(snippets) > 0
        assert all("Python" in s for s in snippets)
        assert total_count == 1

        snippets, total_count = SnippetGenerator.combine_sources(
            None, webvtt, "Python", max_total=3
        )
        assert len(snippets) > 0
        assert total_count == 2

        long_summary = "Python " * 10
        snippets, total_count = SnippetGenerator.combine_sources(
            long_summary, webvtt, "Python", max_total=2
        )
        assert len(snippets) == 2
        assert total_count >= 10

    def test_match_counting_sum_logic(self):
        """Test that match counting correctly sums matches from both sources."""
        summary = "data science uses data analysis and data mining techniques"
        webvtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Big data processing

00:00:02.000 --> 00:00:04.000
data visualization and data storage"""

        snippets, total_count = SnippetGenerator.combine_sources(
            summary, webvtt, "data", max_total=3
        )
        assert total_count == 6
        assert len(snippets) <= 3

        summary_snippets, summary_count = SnippetGenerator.combine_sources(
            summary, None, "data", max_total=3
        )
        assert summary_count == 3

        webvtt_snippets, webvtt_count = SnippetGenerator.combine_sources(
            None, webvtt, "data", max_total=3
        )
        assert webvtt_count == 3

        # combine_sources requires at least one source to be present
        with pytest.raises(AssertionError, match="At least one source must be present"):
            SnippetGenerator.combine_sources(None, None, "data", max_total=3)

    def test_edge_cases(self):
        """Test edge cases for the pure functions."""
        text = "Test with special: @#$%^&*() characters"
        snippets = SnippetGenerator.generate(text, "@#$%")
        assert len(snippets) > 0

        long_query = "a" * 100
        snippets = SnippetGenerator.generate("Some text", long_query)
        assert snippets == []

        text = "Unicode test: café, naïve, 日本語"
        snippets = SnippetGenerator.generate(text, "café")
        assert len(snippets) > 0
        assert "café" in snippets[0]
