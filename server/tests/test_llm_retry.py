"""Tests for LLM parse error recovery with feedback loop"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from reflector.llm import LLM


class TestResponse(BaseModel):
    """Test response model for structured output"""

    title: str = Field(description="A title")
    summary: str = Field(description="A summary")
    confidence: float = Field(description="Confidence score", ge=0, le=1)


class TestLLMParseErrorRecovery:
    """Test parse error recovery with feedback loop"""

    @pytest.mark.asyncio
    async def test_parse_error_recovery_with_feedback(self, test_settings):
        """Test that parse errors trigger retry with error feedback"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 1:
                    return "Analysis"
                else:
                    prompt = args[0]
                    assert "Your previous response had errors:" in prompt
                    return "Analysis with corrections"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            try:
                TestResponse.model_validate({"title": "Test Title"})
            except ValidationError as e:
                validation_error = e

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            mock_program.acall = AsyncMock(
                side_effect=[validation_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response
            assert mock_program.acall.call_count == 2
            assert response_counter["count"] == 2

    @pytest.mark.asyncio
    async def test_json_syntax_error_recovery(self, test_settings):
        """Test recovery from JSON syntax errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 2:
                    prompt = args[0]
                    assert "Invalid JSON syntax" in prompt
                    assert "position 17" in prompt
                return "Analysis"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            json_error = json.JSONDecodeError(
                "Expecting comma delimiter",
                '{"title": "Test" "summary": "Missing comma"}',
                17,
            )

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            mock_program.acall = AsyncMock(
                side_effect=[json_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response
            assert mock_program.acall.call_count == 2
            assert response_counter["count"] == 2

    @pytest.mark.asyncio
    async def test_max_parse_retry_attempts(self, test_settings):
        """Test that parse error retry stops after max attempts"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer
            mock_summarizer.aget_response = AsyncMock(return_value="Analysis")

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            try:
                TestResponse.model_validate({"title": "Test"})
            except ValidationError as e:
                validation_error = e

            mock_program.acall = AsyncMock(side_effect=validation_error)

            with pytest.raises(ValidationError):
                await llm.get_structured_response(
                    prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
                )

            expected_attempts = test_settings.LLM_PARSE_RETRY_ATTEMPTS
            assert mock_program.acall.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_raw_response_logging_on_parse_error(self, test_settings, caplog):
        """Test that raw response is logged when parse error occurs"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
            caplog.at_level("ERROR"),
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer
            mock_summarizer.aget_response = AsyncMock(
                return_value="Analysis response from LLM"
            )

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            try:
                TestResponse.model_validate({"title": "Test"})
            except ValidationError as e:
                validation_error = e

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            mock_program.acall = AsyncMock(
                side_effect=[validation_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response

            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            raw_response_logged = any("Raw response:" in r.message for r in error_logs)
            assert raw_response_logged, "Raw response should be logged on parse error"

    @pytest.mark.asyncio
    async def test_multiple_validation_errors_in_feedback(self, test_settings):
        """Test that all validation errors are included in feedback"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 2:
                    prompt = args[0]
                    # Should contain multiple field errors
                    assert "title" in prompt or "summary" in prompt
                    assert "Schema validation errors" in prompt
                return "Analysis"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # Create validation error with multiple missing fields
            try:
                TestResponse.model_validate({"confidence": 0.5})
            except ValidationError as e:
                validation_error = e

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            mock_program.acall = AsyncMock(
                side_effect=[validation_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response
            assert response_counter["count"] == 2

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, test_settings):
        """Test that no retry happens when first attempt succeeds"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer
            mock_summarizer.aget_response = AsyncMock(return_value="Analysis")

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            mock_program.acall = AsyncMock(return_value=successful_response)

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response
            assert mock_program.acall.call_count == 1
            assert mock_summarizer.aget_response.call_count == 1
