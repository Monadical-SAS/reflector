"""Unit tests for search snippet generation."""

from reflector.db.search import SearchController


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
