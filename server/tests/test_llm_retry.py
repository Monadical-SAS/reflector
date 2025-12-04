"""Tests for LLM parse error recovery using llama-index Workflow"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from reflector.llm import LLM, LLMParseError, StructuredOutputWorkflow


class TestResponse(BaseModel):
    """Test response model for structured output"""

    title: str = Field(description="A title")
    summary: str = Field(description="A summary")
    confidence: float = Field(description="Confidence score", ge=0, le=1)


class TestLLMParseErrorRecovery:
    """Test parse error recovery with Workflow feedback loop"""

    @pytest.mark.asyncio
    async def test_parse_error_recovery_with_feedback(self, test_settings):
        """Test that parse errors trigger retry with error feedback"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            call_count = {"count": 0}

            async def response_handler(prompt, *args, **kwargs):
                call_count["count"] += 1
                if call_count["count"] == 1:
                    # First call returns invalid JSON
                    return '{"title": "Test"}'  # Missing required fields
                else:
                    # Second call should have error feedback with wrong output in prompt
                    assert "Your previous response could not be parsed:" in prompt
                    assert '{"title": "Test"}' in prompt
                    assert "Error:" in prompt
                    assert "Please try again" in prompt
                    return '{"title": "Test", "summary": "Summary", "confidence": 0.95}'

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result.title == "Test"
            assert result.summary == "Summary"
            assert result.confidence == 0.95
            assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_max_parse_retry_attempts(self, test_settings):
        """Test that parse error retry stops after max attempts"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Always return invalid JSON
            mock_summarizer.aget_response = AsyncMock(
                return_value='{"invalid": "missing required fields"}'
            )

            with pytest.raises(LLMParseError, match="Failed to parse"):
                await llm.get_structured_response(
                    prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
                )

            expected_attempts = test_settings.LLM_PARSE_MAX_RETRIES + 1
            assert mock_summarizer.aget_response.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_raw_response_logging_on_parse_error(self, test_settings, caplog):
        """Test that raw response is logged when parse error occurs"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            caplog.at_level("ERROR"),
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            call_count = {"count": 0}

            async def response_handler(*args, **kwargs):
                call_count["count"] += 1
                if call_count["count"] == 1:
                    return '{"title": "Test"}'  # Invalid
                return '{"title": "Test", "summary": "Summary", "confidence": 0.95}'

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result.title == "Test"

            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            raw_response_logged = any("Raw response:" in r.message for r in error_logs)
            assert raw_response_logged, "Raw response should be logged on parse error"

    @pytest.mark.asyncio
    async def test_multiple_validation_errors_in_feedback(self, test_settings):
        """Test that validation errors are included in feedback"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            call_count = {"count": 0}

            async def response_handler(prompt, *args, **kwargs):
                call_count["count"] += 1
                if call_count["count"] == 1:
                    # Missing title and summary
                    return '{"confidence": 0.5}'
                else:
                    # Should have schema validation errors in prompt
                    assert (
                        "Schema validation errors" in prompt
                        or "error" in prompt.lower()
                    )
                    return '{"title": "Test", "summary": "Summary", "confidence": 0.95}'

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result.title == "Test"
            assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, test_settings):
        """Test that no retry happens when first attempt succeeds"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            mock_summarizer.aget_response = AsyncMock(
                return_value='{"title": "Test", "summary": "Summary", "confidence": 0.95}'
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result.title == "Test"
            assert result.summary == "Summary"
            assert result.confidence == 0.95
            assert mock_summarizer.aget_response.call_count == 1


class TestStructuredOutputWorkflow:
    """Direct tests for the StructuredOutputWorkflow"""

    @pytest.mark.asyncio
    async def test_workflow_retries_on_validation_error(self):
        """Test workflow retries when validation fails"""
        workflow = StructuredOutputWorkflow(
            output_cls=TestResponse,
            max_retries=3,
            timeout=30,
        )

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            call_count = {"count": 0}

            async def response_handler(*args, **kwargs):
                call_count["count"] += 1
                if call_count["count"] < 2:
                    return '{"title": "Only title"}'
                return '{"title": "Test", "summary": "Summary", "confidence": 0.9}'

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            result = await workflow.run(
                prompt="Extract data",
                texts=["Some text"],
                tone_name=None,
            )

            assert "success" in result
            assert result["success"].title == "Test"
            assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_workflow_returns_error_after_max_retries(self):
        """Test workflow returns error after exhausting retries"""
        workflow = StructuredOutputWorkflow(
            output_cls=TestResponse,
            max_retries=2,
            timeout=30,
        )

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Always return invalid
            mock_summarizer.aget_response = AsyncMock(return_value='{"invalid": true}')

            result = await workflow.run(
                prompt="Extract data",
                texts=["Some text"],
                tone_name=None,
            )

            assert "error" in result
            assert mock_summarizer.aget_response.call_count == 2
