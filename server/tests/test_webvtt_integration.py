"""Integration tests for WebVTT functionality with real transcript data."""
import pytest
from reflector.processors.types import Word
from reflector.db.transcripts import TranscriptTopic


class TestWebVTTIntegration:
    """Test WebVTT integration with realistic data."""
    
    def test_webvtt_with_realistic_transcript(self):
        """Test WebVTT generation with realistic transcript data."""
        from reflector.utils.webvtt import topics_to_webvtt
        
        # Create realistic topic data (simulating post-diarization state)
        class MockTopic:
            def __init__(self, words):
                self.words = words
        
        # Sample realistic transcript with speaker changes
        topics = [
            MockTopic([
                Word(text="Hello", start=0.0, end=0.5, speaker=0),
                Word(text=" everyone,", start=0.5, end=1.0, speaker=0),
                Word(text=" welcome", start=1.0, end=1.5, speaker=0),
                Word(text=" to", start=1.5, end=1.7, speaker=0),
                Word(text=" the", start=1.7, end=1.9, speaker=0),
                Word(text=" meeting.", start=1.9, end=2.5, speaker=0),
            ]),
            MockTopic([
                Word(text="Thanks", start=3.0, end=3.5, speaker=1),
                Word(text=" for", start=3.5, end=3.7, speaker=1),
                Word(text=" having", start=3.7, end=4.0, speaker=1),
                Word(text=" me.", start=4.0, end=4.5, speaker=1),
                Word(text=" Let's", start=5.0, end=5.3, speaker=0),
                Word(text=" get", start=5.3, end=5.5, speaker=0),
                Word(text=" started.", start=5.5, end=6.0, speaker=0),
            ])
        ]
        
        result = topics_to_webvtt(topics)
        
        # Verify basic WebVTT structure
        assert result.startswith("WEBVTT")
        
        # Verify speaker tags are present
        assert "<v Speaker0>" in result
        assert "<v Speaker1>" in result
        
        # Verify content is present
        assert "Hello everyone, welcome to the meeting." in result
        assert "Thanks for having me." in result
        assert "Let's get started." in result
        
        # Verify timestamps are properly formatted
        assert "00:00:00.000 -->" in result
        assert "00:00:06.000" in result
        
        print("Generated WebVTT:")
        print(result)
    
    def test_webvtt_with_empty_topics(self):
        """Test WebVTT generation with empty topics."""
        from reflector.utils.webvtt import topics_to_webvtt
        
        result = topics_to_webvtt([])
        assert result.strip() == "WEBVTT"
    
    def test_webvtt_with_known_speaker(self):
        """Test WebVTT generation with known speaker."""
        from reflector.utils.webvtt import words_to_webvtt
        
        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text=" world.", start=0.5, end=1.0, speaker=0),
        ]
        
        result = words_to_webvtt(words)
        
        assert "WEBVTT" in result
        assert "Hello world." in result
        # Should have speaker tags when speaker is known
        assert "<v Speaker0>" in result
    
    def test_webvtt_without_speaker_info(self):
        """Test WebVTT generation before diarization (no speaker info)."""
        # This simulates what happens if WebVTT is generated before diarization
        # Words have default speaker=0 but conceptually no real speaker assignment
        from reflector.utils.webvtt import words_to_webvtt
        from reflector.processors.types import TranscriptSegment, Transcript
        
        # Create a mock scenario where segments don't have speaker info
        # We'll create segments manually to simulate this
        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text=" world.", start=0.5, end=1.0, speaker=0),
        ]
        
        result = words_to_webvtt(words)
        
        # Should still work, just with speaker tags
        assert "WEBVTT" in result
        assert "Hello world." in result
        assert "<v Speaker0>" in result  # Default speaker 0 is still a valid speaker
    
    def test_transcript_model_has_webvtt_field(self):
        """Test that Transcript model has the webvtt field."""
        from reflector.db.transcripts import Transcript, SourceKind
        
        # Create a transcript instance to verify the field exists
        transcript = Transcript(
            source_kind=SourceKind.FILE,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest"
        )
        
        assert transcript.webvtt is not None
        assert "WEBVTT" in transcript.webvtt
    
    def test_static_words_to_segments_works(self):
        """Test that the static words_to_segments method works correctly."""
        from reflector.processors.types import Transcript, Word
        
        words = [
            Word(text="Hello", start=0.0, end=0.5, speaker=0),
            Word(text=" world.", start=0.5, end=1.0, speaker=0),
            Word(text=" How", start=2.0, end=2.3, speaker=1),
            Word(text=" are", start=2.3, end=2.5, speaker=1),
            Word(text=" you?", start=2.5, end=3.0, speaker=1),
        ]
        
        # Test static method
        segments = Transcript.words_to_segments(words)
        
        assert len(segments) == 2  # Two segments due to speaker change
        assert segments[0].speaker == 0
        assert segments[1].speaker == 1
        assert "Hello world." in segments[0].text
        assert "How are you?" in segments[1].text
        
        # Test backward compatibility
        transcript = Transcript(words=words)
        segments_compat = transcript.as_segments()
        
        assert len(segments_compat) == len(segments)
        assert segments_compat[0].text == segments[0].text