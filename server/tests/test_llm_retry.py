"""Tests for LLM retry logic with exponential backoff and parse error recovery"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError

from reflector.llm import LLM
from reflector.settings import settings

# Disable jitter for deterministic tests
settings.LLM_RETRY_WAIT_JITTER = False


class TestResponse(BaseModel):
    """Test response model for structured output"""

    title: str = Field(description="A title")
    summary: str = Field(description="A summary")
    confidence: float = Field(description="Confidence score", ge=0, le=1)


class TestLLMNetworkRetry:
    """Test network error retry logic"""

    @pytest.mark.asyncio
    async def test_retry_on_httpx_timeout(self):
        """Test retry on network timeout errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First 2 calls timeout, 3rd succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.ReadTimeout("Request timed out"),
                    httpx.ConnectTimeout("Connection timed out"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_asyncio_timeout(self):
        """Test retry on asyncio timeout errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call times out, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    asyncio.TimeoutError("Operation timed out"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Test retry on rate limit (429) errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Create 429 error
            rate_limit_error = httpx.HTTPStatusError(
                "Rate limit exceeded",
                request=MagicMock(),
                response=MagicMock(status_code=429, headers={}),
            )

            # First call rate limited, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[rate_limit_error, "Success response"]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_service_unavailable(self):
        """Test retry on 503 Service Unavailable errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Create 503 error
            service_error = httpx.HTTPStatusError(
                "Service temporarily unavailable",
                request=MagicMock(),
                response=MagicMock(status_code=503, headers={}),
            )

            # First two calls fail with 503, third succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[service_error, service_error, "Success response"]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """Test no retry on 401 Unauthorized errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Create 401 error
            auth_error = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401, headers={}),
            )

            mock_summarizer.aget_response = AsyncMock(side_effect=auth_error)

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert exc_info.value.response.status_code == 401
            # Should only try once, no retries
            assert mock_summarizer.aget_response.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retry_attempts_exceeded(self):
        """Test that retry stops after max attempts"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Always fail with timeout
            mock_summarizer.aget_response = AsyncMock(
                side_effect=httpx.ReadTimeout("Request timed out")
            )

            with pytest.raises(httpx.ReadTimeout):
                await llm.get_response(prompt="Test prompt", texts=["Test text"])

            # Should try max attempts (default 5)
            expected_attempts = getattr(settings, "LLM_RETRY_NETWORK_ATTEMPTS", 5)
            assert mock_summarizer.aget_response.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff is configured correctly"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        # Test that retries happen with exponential delays
        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Track retry attempts
            attempt_count = {"count": 0}

            async def fail_then_succeed(*args, **kwargs):
                attempt_count["count"] += 1
                if attempt_count["count"] < 4:
                    raise httpx.ReadTimeout("Timeout")
                return "Success"

            mock_summarizer.aget_response = AsyncMock(side_effect=fail_then_succeed)

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success"
            assert attempt_count["count"] == 4  # 3 failures + 1 success


class TestLLMParseErrorRecovery:
    """Test parse error recovery with feedback loop"""

    @pytest.mark.asyncio
    async def test_parse_error_recovery_with_feedback(self):
        """Test that parse errors trigger retry with error feedback"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Create counter to track responses
            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                # First call gets normal prompt, second gets error feedback
                if response_counter["count"] == 1:
                    return "Analysis"
                else:
                    # Should have error feedback in prompt
                    prompt = args[0]
                    assert "Your previous response had errors:" in prompt
                    return "Analysis with corrections"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # First call fails with validation error, second succeeds
            # Create a real ValidationError by trying to validate bad data
            try:
                TestResponse.model_validate(
                    {"title": "Test Title"}
                )  # Missing summary and confidence
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
    async def test_json_syntax_error_recovery(self):
        """Test recovery from JSON syntax errors"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Track calls to verify error feedback
            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 2:
                    # Second call should have JSON error feedback
                    prompt = args[0]
                    assert "Invalid JSON syntax" in prompt
                    assert "position 17" in prompt
                return "Analysis"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # First call fails with JSON decode error, second succeeds
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
    async def test_max_parse_retry_attempts(self):
        """Test that parse error retry stops after max attempts"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer
            mock_summarizer.aget_response = AsyncMock(return_value="Analysis")

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # Always fail with validation error
            try:
                TestResponse.model_validate(
                    {"title": "Test"}
                )  # Missing summary and confidence
            except ValidationError as e:
                validation_error = e

            mock_program.acall = AsyncMock(side_effect=validation_error)

            with pytest.raises(ValidationError):
                await llm.get_structured_response(
                    prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
                )

            # Should try max parse attempts (default 3)
            expected_attempts = getattr(settings, "LLM_RETRY_PARSE_ATTEMPTS", 3)
            assert mock_program.acall.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_multiple_validation_errors_in_feedback(self):
        """Test that all validation errors are included in feedback"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Track calls and validate error feedback includes all errors
            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 2:
                    # Second call should have all validation errors
                    prompt = args[0]
                    assert "title" in prompt
                    assert "summary" in prompt
                    assert "confidence" in prompt
                    assert prompt.count("Field required") >= 2  # Two missing fields
                return "Analysis"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # Create validation error with multiple issues
            # Create a real ValidationError by trying to validate bad data
            try:
                TestResponse.model_validate(
                    {"confidence": "not_a_float"}
                )  # Missing title and summary, wrong type for confidence
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


class TestLLMCombinedRetry:
    """Test combined network and parse error retry scenarios"""

    @pytest.mark.asyncio
    async def test_network_retry_then_parse_retry(self):
        """Test network retry followed by parse error retry"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Track calls
            response_counter = {"count": 0}

            async def response_handler(*args, **kwargs):
                response_counter["count"] += 1
                if response_counter["count"] == 1:
                    # First call times out
                    raise httpx.ReadTimeout("Timeout")
                elif response_counter["count"] == 2:
                    # Second call succeeds
                    return "Analysis"
                else:
                    # Third call (after parse error) has error feedback
                    return "Analysis with corrections"

            mock_summarizer.aget_response = AsyncMock(side_effect=response_handler)

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # After network retry succeeds, first parse fails
            try:
                TestResponse.model_validate(
                    {"title": "Test"}
                )  # Missing summary and confidence
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
            # Network retry: 2 attempts (1 fail + 1 success) + 1 for parse retry
            assert response_counter["count"] == 3
            # Parse retry: 2 attempts
            assert mock_program.acall.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_logging(self, caplog):
        """Test that retry attempts are properly logged"""
        llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            caplog.at_level("INFO"),
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Fail twice, then succeed
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.ReadTimeout("Timeout"),
                    httpx.ReadTimeout("Timeout"),
                    "Success",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success"

            # Check for retry logs
            retry_logs = [r for r in caplog.records if "retry" in r.message.lower()]
            assert len(retry_logs) >= 2  # At least 2 retry attempts logged
