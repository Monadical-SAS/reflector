"""Test WebVTT format snippet generation with smart truncation."""

from io import StringIO

import pytest
import webvtt

from reflector.db.search import SearchController
from reflector.utils.webvtt_types import Webvtt, cast_webvtt


class TestWebVTTFormatSnippets:
    """Test cases for WebVTT format snippet generation with truncation.

    IMPORTANT DESIGN DECISIONS:
    1. Match captions CAN be truncated (but match text is preserved)
    2. Timestamps are NEVER adjusted (remain original even for truncated text)
    3. Length calculation is for TEXTUAL content only (not WebVTT format overhead)
    """

    def test_returns_valid_webvtt_format(self):
        """Test that snippets are valid WebVTT format."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>The quick brown fox jumps over the lazy dog

00:00:05.000 --> 00:00:10.000
<v Speaker1>Another sentence here with keyword inside

00:00:10.000 --> 00:00:15.000
<v Speaker2>Final caption in the transcript
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1, snippet_max_length=500
        )

        assert len(snippets) == 1
        snippet = snippets[0]

        # Should be valid WebVTT format
        assert isinstance(snippet, str)  # Will be WebvttText after implementation
        assert snippet.startswith("WEBVTT")

        # Should be parseable
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)
        assert len(parsed.captions) > 0

        # Should contain the match
        full_text = " ".join(cap.text for cap in parsed.captions)
        assert "keyword" in full_text.lower()

    def test_truncates_context_captions_by_words(self):
        """Test word-based truncation of context captions."""
        # Create long context captions
        long_before = " ".join([f"word{i}" for i in range(100)])  # 100 words
        long_after = " ".join([f"after{i}" for i in range(100)])  # 100 words

        webvtt_content = cast_webvtt(f"""WEBVTT

00:00:00.000 --> 00:00:30.000
<v Speaker0>{long_before}

00:00:30.000 --> 00:00:35.000
<v Speaker1>This caption has the keyword match here

00:00:35.000 --> 00:01:05.000
<v Speaker2>{long_after}
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword match", max_snippets=1, snippet_max_length=300
        )

        assert len(snippets) == 1
        snippet = snippets[0]

        # Parse the snippet
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        assert len(parsed.captions) == 3

        # Before caption should be truncated from the end
        before_text = parsed.captions[0].text
        assert before_text.startswith("...")  # Ellipsis for truncation
        assert "word99" in before_text  # Should have last words
        assert "word0" not in before_text  # Should not have first words

        # Match caption should be complete
        match_text = parsed.captions[1].text
        assert "keyword match" in match_text
        assert not match_text.startswith("...")
        assert not match_text.endswith("...")

        # After caption should be truncated from the beginning
        after_text = parsed.captions[2].text
        assert after_text.endswith("...")  # Ellipsis for truncation
        assert "after0" in after_text  # Should have first words
        assert "after99" not in after_text  # Should not have last words

    def test_timestamps_not_adjusted_for_truncated_captions(self):
        """Test that timestamps are NOT adjusted even for truncated content.

        IMPORTANT: We keep original timestamps even if showing only a small
        portion of the caption. This is by design.
        """
        # 10-second caption with 100 words
        long_text = " ".join([f"word{i}" for i in range(100)])

        webvtt_content = cast_webvtt(f"""WEBVTT

00:00:00.000 --> 00:00:10.000
<v Speaker0>{long_text}

00:00:10.000 --> 00:00:15.000
<v Speaker1>Match keyword here

00:00:15.000 --> 00:00:25.000
<v Speaker2>{long_text}
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1, snippet_max_length=250
        )

        snippet = snippets[0]
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        # IMPORTANT: Timestamps should remain UNCHANGED even if text is truncated
        first_cap = parsed.captions[0]
        # Should keep original timestamp even if showing only partial text
        assert first_cap.start == "00:00:00.000"
        assert first_cap.end == "00:00:10.000"

        # Last caption should also keep original timestamps
        last_cap = parsed.captions[-1]
        assert last_cap.start == "00:00:15.000"
        assert last_cap.end == "00:00:25.000"

        # Timestamps should still be in order
        for i in range(len(parsed.captions) - 1):
            assert parsed.captions[i].end <= parsed.captions[i + 1].start

    def test_multiple_matches_in_snippet(self):
        """Test handling multiple matches that fit in one snippet."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>First caption

00:00:05.000 --> 00:00:10.000
<v Speaker1>Testing keyword one

00:00:10.000 --> 00:00:15.000
<v Speaker2>Testing keyword two

00:00:15.000 --> 00:00:20.000
<v Speaker3>Testing keyword three

00:00:20.000 --> 00:00:25.000
<v Speaker4>Last caption
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=3, snippet_max_length=600
        )

        # If all matches fit, should return single snippet
        assert len(snippets) == 1

        snippet = snippets[0]
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        # Should include all captions since they fit
        assert len(parsed.captions) == 5

        # All match captions should be complete
        text = " ".join(cap.text for cap in parsed.captions)
        assert text.count("keyword") == 3

    def test_very_long_match_caption_gets_truncated(self):
        """Test that match captions CAN be truncated to fit max_length.

        IMPORTANT: Match captions are truncated but the match itself is preserved
        in the truncation with context around it.
        """
        # Match caption itself is 1000+ characters
        long_match = (
            "prefix "
            + " ".join([f"word{i}" for i in range(100)])
            + " keyword "
            + " ".join([f"after{i}" for i in range(100)])
        )

        webvtt_content = cast_webvtt(f"""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>Before caption

00:00:05.000 --> 00:00:35.000
<v Speaker1>{long_match}

00:00:35.000 --> 00:00:40.000
<v Speaker2>After caption
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt,
            "keyword",
            max_snippets=1,
            snippet_max_length=100,  # Much smaller than match caption
        )

        assert len(snippets) == 1
        snippet = snippets[0]

        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        # Match caption should be truncated but preserve the match
        match_caption = None
        for cap in parsed.captions:
            if "keyword" in cap.text.lower():
                match_caption = cap
                break

        assert match_caption is not None
        # The match "keyword" should be preserved
        assert "keyword" in match_caption.text.lower()
        # But the caption should be truncated (much shorter than original)
        assert len(match_caption.text) < len(long_match) / 2
        # Should have ellipsis indicating truncation
        assert "..." in match_caption.text

    def test_throws_on_no_matches(self):
        """Test that function throws when no matches found."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>Some content here

00:00:05.000 --> 00:00:10.000
<v Speaker1>More content there
""")

        vtt = Webvtt(webvtt_content)

        with pytest.raises(ValueError) as exc_info:
            SearchController._generate_webvtt_snippets(
                vtt, "nonexistent", max_snippets=1
            )

        assert "No matches found" in str(exc_info.value)
        assert "database already confirmed matches" in str(exc_info.value)

    def test_throws_on_empty_webvtt(self):
        """Test that function throws on empty WebVTT."""
        webvtt_content = cast_webvtt("""WEBVTT

""")

        vtt = Webvtt(webvtt_content)

        with pytest.raises(ValueError) as exc_info:
            SearchController._generate_webvtt_snippets(vtt, "anything", max_snippets=1)

        assert "Empty WebVTT" in str(exc_info.value) or "No captions" in str(
            exc_info.value
        )

    def test_word_boundary_truncation(self):
        """Test that truncation happens at word boundaries."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>The quick brown fox jumps over the lazy dog

00:00:05.000 --> 00:00:10.000
<v Speaker1>Match keyword here

00:00:10.000 --> 00:00:15.000
<v Speaker2>Another quick brown fox jumps over
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1, snippet_max_length=200
        )

        snippet = snippets[0]
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        for cap in parsed.captions:
            text = cap.text
            # Check no partial words (all words should be complete)
            words = text.replace("...", "").strip().split()
            for word in words:
                # Each word should be a complete word, not fragments
                assert len(word) > 0
                assert not word.endswith("-")  # No hyphenated breaks

    def test_speaker_preserved_in_truncated_captions(self):
        """Test speaker tags are preserved even in truncated captions."""
        long_text = " ".join([f"word{i}" for i in range(100)])

        webvtt_content = cast_webvtt(f"""WEBVTT

00:00:00.000 --> 00:00:10.000
<v Alice>{long_text}

00:00:10.000 --> 00:00:15.000
<v Bob>Match keyword here

00:00:15.000 --> 00:00:25.000
<v Charlie>{long_text}
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1, snippet_max_length=250
        )

        snippet = snippets[0]

        # Check raw WebVTT text has speaker tags
        assert "<v Alice>" in snippet or "Alice" in snippet
        assert "<v Bob>" in snippet or "Bob" in snippet
        assert "<v Charlie>" in snippet or "Charlie" in snippet

    def test_asymmetric_context_truncation(self):
        """Test smart context distribution when match is near boundaries."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>First caption with keyword match

00:00:05.000 --> 00:00:10.000
<v Speaker1>Second caption here

00:00:10.000 --> 00:00:15.000
<v Speaker2>Third caption here

00:00:15.000 --> 00:00:20.000
<v Speaker3>Fourth caption here

00:00:20.000 --> 00:00:25.000
<v Speaker4>Fifth caption here
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1, snippet_max_length=400
        )

        snippet = snippets[0]
        buffer = StringIO(snippet)
        parsed = webvtt.read_buffer(buffer)

        # When match is at start, should include at least match + 1 context
        # Our implementation adds 1 caption before/after
        assert len(parsed.captions) >= 2  # Match + at least one context

    def test_returns_webvtt_text_branded_type(self):
        """Test that return type is list of WebvttText branded type."""
        webvtt_content = cast_webvtt("""WEBVTT

00:00:00.000 --> 00:00:05.000
<v Speaker0>Content with keyword here
""")

        vtt = Webvtt(webvtt_content)
        snippets = SearchController._generate_webvtt_snippets(
            vtt, "keyword", max_snippets=1
        )

        assert isinstance(snippets, list)
        assert len(snippets) > 0

        for snippet in snippets:
            # Should be WebvttText type (will fail until implementation)
            assert isinstance(snippet, str)  # Will be WebvttText
            assert snippet.startswith("WEBVTT")
