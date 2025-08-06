"""Tests for WebVTT utilities."""
import pytest
from reflector.processors.types import Word, TranscriptSegment


class TestWordsToWebVTT:
    """Test words_to_webvtt function with TDD approach."""
    
    def test_empty_words_returns_empty_webvtt(self):
        """Should return empty WebVTT structure for empty words list."""
        from reflector.utils.webvtt import words_to_webvtt
        
        result = words_to_webvtt([])
        
        # Empty WebVTT should contain just the header
        assert "WEBVTT" in result
        assert result.strip() == "WEBVTT"
    
    def test_single_word_creates_single_caption(self):
        """Should create one caption for a single word."""
        from reflector.utils.webvtt import words_to_webvtt
        
        words = [Word(text="Hello", start=0.0, end=1.0, speaker=0)]
        result = words_to_webvtt(words)
        
        assert "WEBVTT" in result
        assert "00:00:00.000 --> 00:00:01.000" in result
        assert "Hello" in result
        assert "<v Speaker0>" in result
    
    def test_multiple_words_same_speaker_groups_properly(self):
        """Should group consecutive words from same speaker."""
        from reflector.utils.webvtt import words_to_webvtt
        
        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text=" world", start=0.5, end=1.0, speaker=0),
        ]
        result = words_to_webvtt(words)
        
        assert "WEBVTT" in result
        assert "Hello world" in result
        assert "<v Speaker0>" in result
    
    def test_speaker_change_creates_new_caption(self):
        """Should create new caption when speaker changes."""
        from reflector.utils.webvtt import words_to_webvtt
        
        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text="Hi", start=0.6, end=1.0, speaker=1),
        ]
        result = words_to_webvtt(words)
        
        lines = result.split('\n')
        # Should have two caption blocks
        assert "<v Speaker0>" in result
        assert "<v Speaker1>" in result
        assert "Hello" in result
        assert "Hi" in result
    
    def test_punctuation_creates_segment_boundary(self):
        """Should respect punctuation boundaries from segmentation logic."""
        from reflector.utils.webvtt import words_to_webvtt
        
        # This will depend on the static words_to_segments implementation
        words = [
            Word(text="Hello.", start=0.0, end=0.5, speaker=0),
            Word(text=" How", start=0.6, end=1.0, speaker=0),
            Word(text=" are", start=1.0, end=1.3, speaker=0),
            Word(text=" you?", start=1.3, end=1.8, speaker=0),
        ]
        result = words_to_webvtt(words)
        
        # Should use existing segmentation logic
        assert "WEBVTT" in result
        assert "<v Speaker0>" in result


class TestTopicsToWebVTT:
    """Test topics_to_webvtt function."""
    
    def test_empty_topics_returns_empty_webvtt(self):
        """Should handle empty topics list."""
        from reflector.utils.webvtt import topics_to_webvtt
        
        result = topics_to_webvtt([])
        assert "WEBVTT" in result
        assert result.strip() == "WEBVTT"
    
    def test_extracts_words_from_topics(self):
        """Should extract all words from topics in sequence."""
        from reflector.utils.webvtt import topics_to_webvtt
        
        # Mock topic objects
        class MockTopic:
            def __init__(self, words):
                self.words = words
        
        # Words should be in sequence
        topics = [
            MockTopic([
                Word(text="First", start=0.0, end=0.5, speaker=1),
                Word(text="Second", start=1.0, end=1.5, speaker=0),
            ])
        ]
        
        result = topics_to_webvtt(topics)
        
        # Should process words in the given order
        assert "WEBVTT" in result
        # Words should appear in the order provided
        first_pos = result.find("First")
        second_pos = result.find("Second")
        assert first_pos < second_pos
    
    def test_non_sequential_topics_raises_assertion(self):
        """Should raise assertion error when words are not in chronological sequence."""
        from reflector.utils.webvtt import topics_to_webvtt
        
        # Mock topic objects
        class MockTopic:
            def __init__(self, words):
                self.words = words
        
        # Words out of sequence - second word starts before first
        topics = [
            MockTopic([
                Word(text="Second", start=1.0, end=1.5, speaker=0),
                Word(text="First", start=0.0, end=0.5, speaker=1),
            ])
        ]
        
        # Should raise assertion error for non-sequential words
        with pytest.raises(AssertionError) as exc_info:
            topics_to_webvtt(topics)
        
        assert "Words are not in sequence" in str(exc_info.value)
        assert "Second and First" in str(exc_info.value)


class TestTranscriptWordsToSegments:
    """Test static words_to_segments method (TDD for making it static)."""
    
    def test_static_method_exists(self):
        """Should have static words_to_segments method."""
        from reflector.processors.types import Transcript
        
        # Should be callable without instance
        words = [Word(text="Hello", start=0.0, end=1.0, speaker=0)]
        segments = Transcript.words_to_segments(words)
        
        assert isinstance(segments, list)
        assert len(segments) == 1
        assert segments[0].text == "Hello"
        assert segments[0].speaker == 0
    
    def test_backward_compatibility(self):
        """Should maintain backward compatibility with instance method."""
        from reflector.processors.types import Transcript
        
        words = [Word(text="Hello", start=0.0, end=1.0, speaker=0)]
        transcript = Transcript(words=words)
        
        # Instance method should still work
        segments = transcript.as_segments()
        assert isinstance(segments, list)
        assert len(segments) == 1
        assert segments[0].text == "Hello"