"""
Tests for the template-aware transcript chunker.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
import structlog
from typing import List, Dict, Any

from transcript_chunker import (
    process_transcript_with_template_aware_chunking,
    find_natural_split_point,
    _generate_chunks_with_overlap,
    _shrink_chunk_to_fit,
)


class MockMessages:
    """Mock Messages class for testing."""
    
    def __init__(self, messages=None, tokenizer=None):
        self.messages = messages or []
        self.tokenizer = tokenizer or MockTokenizer()
    
    def copy(self):
        return MockMessages(self.messages[:], self.tokenizer)
    
    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})
    
    def count_tokens(self):
        total = 0
        for msg in self.messages:
            total += len(self.tokenizer.tokenize(msg["content"]))
        return total


class MockTokenizer:
    """Mock tokenizer for testing."""
    
    def __init__(self, chars_per_token: float = 4.0):
        self.chars_per_token = chars_per_token
    
    def tokenize(self, text: str) -> List[str]:
        """Mock tokenization - splits by approximate character count."""
        if not text:
            return []
        tokens = []
        for i in range(0, len(text), int(self.chars_per_token)):
            tokens.append(text[i:i+int(self.chars_per_token)])
        return tokens


class TestTemplateAwareChunking:
    """Test the main template-aware chunking function."""
    
    @pytest.mark.asyncio
    async def test_single_chunk_no_splitting(self):
        """Test when transcript fits in single chunk."""
        transcript = "Short transcript that fits in one chunk."
        
        # Mock setup
        tokenizer = MockTokenizer(chars_per_token=4.0)
        messages_template = MockMessages([{"role": "system", "content": "You are an assistant."}], tokenizer)
        
        async def mock_llm_completion(messages):
            return {"choices": [{"message": {"content": '["Subject 1", "Subject 2"]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return ["Subject 1", "Subject 2"]
        
        result = await process_transcript_with_template_aware_chunking(
            transcript=transcript,
            messages_template=messages_template,
            max_context_tokens=1000,  # Large enough for single chunk
            llm_completion_func=mock_llm_completion,
            create_prompt_func=mock_create_prompt,
            validate_json_func=mock_validate_json
        )
        
        assert isinstance(result, list)
        assert result == ["Subject 1", "Subject 2"]
    
    @pytest.mark.asyncio
    async def test_multiple_chunks_with_overlap(self):
        """Test transcript that requires multiple chunks."""
        transcript = "A" * 1000  # Long transcript
        
        # Mock setup
        tokenizer = MockTokenizer(chars_per_token=4.0)
        messages_template = MockMessages([{"role": "system", "content": "You are an assistant."}], tokenizer)
        
        async def mock_llm_completion(messages):
            return {"choices": [{"message": {"content": '["Subject A", "Subject B"]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return ["Subject A", "Subject B"]
        
        result = await process_transcript_with_template_aware_chunking(
            transcript=transcript,
            messages_template=messages_template,
            max_context_tokens=100,  # Small to force chunking
            llm_completion_func=mock_llm_completion,
            create_prompt_func=mock_create_prompt,
            validate_json_func=mock_validate_json,
            overlap_ratio=0.15
        )
        
        assert isinstance(result, list)
        # Should have deduplicated results
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_template_overhead_too_large(self):
        """Test error when template overhead exceeds context limit."""
        transcript = "Test transcript"
        
        # Mock setup - tokenizer that returns many tokens for template
        class LargeTokenizer:
            def tokenize(self, text):
                return ["token"] * (len(text) * 10)  # Very large token count
        
        tokenizer = LargeTokenizer()
        messages_template = MockMessages([{"role": "system", "content": "Very long system prompt" * 100}], tokenizer)
        
        async def mock_llm_completion(messages):
            return {"choices": [{"message": {"content": '[]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return []
        
        with pytest.raises(ValueError, match="Template overhead .* exceeds context limit"):
            await process_transcript_with_template_aware_chunking(
                transcript=transcript,
                messages_template=messages_template,
                max_context_tokens=50,  # Very small limit
                llm_completion_func=mock_llm_completion,
                create_prompt_func=mock_create_prompt,
                validate_json_func=mock_validate_json
            )
    
    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        """Test with empty transcript."""
        tokenizer = MockTokenizer()
        messages_template = MockMessages([{"role": "system", "content": "Assistant"}], tokenizer)
        
        async def mock_llm_completion(messages):
            return {"choices": [{"message": {"content": '[]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return []
        
        result = await process_transcript_with_template_aware_chunking(
            transcript="",
            messages_template=messages_template,
            max_context_tokens=1000,
            llm_completion_func=mock_llm_completion,
            create_prompt_func=mock_create_prompt,
            validate_json_func=mock_validate_json
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_invalid_overlap_ratio(self):
        """Test error with invalid overlap ratio."""
        transcript = "Test transcript"
        tokenizer = MockTokenizer()
        messages_template = MockMessages([{"role": "system", "content": "Assistant"}], tokenizer)
        
        async def mock_llm_completion(messages):
            return {"choices": [{"message": {"content": '[]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return []
        
        with pytest.raises(ValueError, match="overlap_ratio must be between 0 and 0.5"):
            await process_transcript_with_template_aware_chunking(
                transcript=transcript,
                messages_template=messages_template,
                max_context_tokens=1000,
                llm_completion_func=mock_llm_completion,
                create_prompt_func=mock_create_prompt,
                validate_json_func=mock_validate_json,
                overlap_ratio=0.6  # Invalid
            )
    
    @pytest.mark.asyncio
    async def test_chunk_error_handling(self):
        """Test handling when some chunks fail."""
        transcript = "A" * 1000  # Long transcript
        
        tokenizer = MockTokenizer(chars_per_token=4.0)
        messages_template = MockMessages([{"role": "system", "content": "Assistant"}], tokenizer)
        
        call_count = 0
        async def mock_llm_completion_with_errors(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First chunk fails")
            else:
                return {"choices": [{"message": {"content": '["Subject B"]'}}]}
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        def mock_validate_json(result):
            return ["Subject B"]
        
        result = await process_transcript_with_template_aware_chunking(
            transcript=transcript,
            messages_template=messages_template,
            max_context_tokens=100,  # Force chunking
            llm_completion_func=mock_llm_completion_with_errors,
            create_prompt_func=mock_create_prompt,
            validate_json_func=mock_validate_json
        )
        
        # Should still return results from successful chunks
        assert isinstance(result, list)


class TestChunkGeneration:
    """Test chunk generation utilities."""
    
    def test_generate_chunks_with_overlap(self):
        """Test chunk generation with overlap."""
        transcript = "Speaker A: Hello. Speaker B: Hi there. Speaker C: Welcome everyone to the meeting."
        tokenizer = MockTokenizer(chars_per_token=4.0)
        logger = structlog.get_logger()
        
        chunks = _generate_chunks_with_overlap(
            transcript=transcript,
            tokenizer=tokenizer,
            core_content_tokens=10,  # Small chunks for testing
            overlap_tokens=2,
            logger=logger
        )
        
        assert len(chunks) >= 1
        # Check that chunks have reasonable content
        for chunk in chunks:
            assert len(chunk.strip()) > 0
    
    def test_shrink_chunk_to_fit(self):
        """Test chunk shrinking functionality."""
        large_chunk = "A" * 1000
        
        tokenizer = MockTokenizer(chars_per_token=4.0)
        messages_template = MockMessages([{"role": "system", "content": "Assistant"}], tokenizer)
        
        def mock_create_prompt(transcript_text):
            return f"Extract subjects from: {transcript_text}"
        
        logger = structlog.get_logger()
        
        shrunk_chunk = _shrink_chunk_to_fit(
            chunk=large_chunk,
            messages_template=messages_template,
            create_prompt_func=mock_create_prompt,
            max_context_tokens=100,  # Small limit
            logger=logger
        )
        
        # Should be smaller than original
        assert len(shrunk_chunk) < len(large_chunk)
        assert len(shrunk_chunk) > 0


class TestNaturalSplitPoint:
    """Test natural split point detection (reused from v1)."""
    
    def test_paragraph_break_detection(self):
        """Test detection of paragraph breaks."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        target_pos = 20
        min_pos = 10
        
        result = find_natural_split_point(text, target_pos, min_pos)
        assert result >= min_pos
        assert result <= target_pos
    
    def test_speaker_change_detection(self):
        """Test detection of speaker changes."""
        text = "Speaker A: First statement.\nSpeaker B: Second statement.\nSpeaker C: Third statement."
        target_pos = 35
        min_pos = 20
        
        result = find_natural_split_point(text, target_pos, min_pos)
        assert result >= min_pos
        assert result <= target_pos
    
    def test_sentence_ending_detection(self):
        """Test detection of sentence endings."""
        text = "This is the first sentence. This is the second sentence. This is the third sentence."
        target_pos = 35
        min_pos = 20
        
        result = find_natural_split_point(text, target_pos, min_pos)
        assert result >= min_pos
        assert result <= target_pos
    
    def test_boundary_conditions(self):
        """Test boundary conditions."""
        text = "Short text"
        
        # Target position at end
        result = find_natural_split_point(text, len(text), 0)
        assert 0 <= result <= len(text)
        
        # Target position equals min position
        result = find_natural_split_point(text, 5, 5)
        assert result == 5


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])