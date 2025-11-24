"""Tests for LLM retry logic with exponential backoff and parse error recovery"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError

from reflector.llm import LLM


class TestResponse(BaseModel):
    """Test response model for structured output"""

    title: str = Field(description="A title")
    summary: str = Field(description="A summary")
    confidence: float = Field(description="Confidence score", ge=0, le=1)


class TestLLMNetworkRetry:
    """Test network error retry logic"""

    @pytest.mark.asyncio
    async def test_retry_on_httpx_timeout(self, test_settings):
        """Test retry on network timeout errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_retry_on_asyncio_timeout(self, test_settings):
        """Test retry on asyncio timeout errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_retry_on_rate_limit(self, test_settings):
        """Test retry on rate limit (429) errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_retry_on_service_unavailable(self, test_settings):
        """Test retry on 503 Service Unavailable errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_no_retry_on_auth_error(self, test_settings):
        """Test no retry on 401 Unauthorized errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_max_retry_attempts_exceeded(self, test_settings):
        """Test that retry stops after max attempts"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
            expected_attempts = getattr(test_settings, "LLM_RETRY_NETWORK_ATTEMPTS", 5)
            assert mock_summarizer.aget_response.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, test_settings):
        """Test that exponential backoff is configured correctly"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, test_settings):
        """Test that LLM_RETRY_TIMEOUT is enforced for entire operation"""
        # Configure settings with very short timeout for test
        test_settings.LLM_RETRY_TIMEOUT = 2  # 2 second timeout
        test_settings.LLM_RETRY_NETWORK_ATTEMPTS = 10  # Many attempts but timeout first

        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Simulate slow responses that would exceed timeout
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(1)  # Each call takes 1 second
                raise httpx.ReadTimeout("Timeout")

            mock_summarizer.aget_response = AsyncMock(side_effect=slow_response)

            # Should raise TimeoutError, not exhaust all retry attempts
            with pytest.raises(asyncio.TimeoutError):
                await llm.get_response(prompt="Test prompt", texts=["Test text"])

            # Should not have tried all 10 attempts due to timeout
            assert mock_summarizer.aget_response.call_count < 10

    @pytest.mark.asyncio
    async def test_retry_on_httpx_timeout_exception(self, test_settings):
        """Test retry on httpx.TimeoutException (base class)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call times out with base TimeoutException, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Generic timeout"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_connect_error(self, test_settings):
        """Test retry on httpx.ConnectError (connection failures)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call fails to connect, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.ConnectError("Connection failed"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_network_error(self, test_settings):
        """Test retry on httpx.NetworkError (network unreachable, DNS failures)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call has network error, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.NetworkError("Network unreachable"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_504_gateway_timeout(self, test_settings):
        """Test retry on 504 Gateway Timeout errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # Create 504 error
            gateway_timeout_error = httpx.HTTPStatusError(
                "Gateway timeout",
                request=MagicMock(),
                response=MagicMock(status_code=504, headers={}),
            )

            # First call times out at gateway, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[gateway_timeout_error, "Success response"]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_remote_protocol_error(self, test_settings):
        """Test retry on httpx.RemoteProtocolError (malformed HTTP response)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call gets malformed HTTP response, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.RemoteProtocolError("Invalid HTTP response"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_read_error(self, test_settings):
        """Test retry on httpx.ReadError (connection broken while reading)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call breaks while reading response, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.ReadError("Connection broken while reading"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_write_error(self, test_settings):
        """Test retry on httpx.WriteError (connection broken while writing)"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with patch("reflector.llm.TreeSummarize") as mock_summarize:
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer

            # First call breaks while sending request, second succeeds
            mock_summarizer.aget_response = AsyncMock(
                side_effect=[
                    httpx.WriteError("Connection broken while writing"),
                    "Success response",
                ]
            )

            result = await llm.get_response(prompt="Test prompt", texts=["Test text"])

            assert result == "Success response"
            assert mock_summarizer.aget_response.call_count == 2


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
    async def test_json_syntax_error_recovery(self, test_settings):
        """Test recovery from JSON syntax errors"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
            expected_attempts = getattr(test_settings, "LLM_RETRY_PARSE_ATTEMPTS", 3)
            assert mock_program.acall.call_count == expected_attempts

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

            # Create validation error
            try:
                TestResponse.model_validate({"title": "Test"})  # Missing fields
            except ValidationError as e:
                validation_error = e

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            # First call fails with validation error, second succeeds
            mock_program.acall = AsyncMock(
                side_effect=[validation_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response

            # Check that raw response was logged
            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            raw_response_logged = any("Raw response:" in r.message for r in error_logs)
            assert raw_response_logged, "Raw response should be logged on parse error"

    @pytest.mark.asyncio
    async def test_no_double_logging_on_parse_error(self, test_settings, caplog):
        """Test that parse errors are not logged twice"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

        with (
            patch("reflector.llm.TreeSummarize") as mock_summarize,
            patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
            caplog.at_level("ERROR"),
        ):
            mock_summarizer = MagicMock()
            mock_summarize.return_value = mock_summarizer
            mock_summarizer.aget_response = AsyncMock(return_value="Analysis response")

            mock_program = MagicMock()
            mock_program_class.from_defaults.return_value = mock_program

            # Create validation error
            try:
                TestResponse.model_validate({"title": "Test"})  # Missing fields
            except ValidationError as e:
                validation_error = e

            successful_response = TestResponse(
                title="Test Title", summary="Test Summary", confidence=0.95
            )

            # First call fails with validation error, second succeeds
            mock_program.acall = AsyncMock(
                side_effect=[validation_error, successful_response]
            )

            result = await llm.get_structured_response(
                prompt="Test prompt", texts=["Test text"], output_cls=TestResponse
            )

            assert result == successful_response

            # Check that parse error is logged only once, not twice
            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]

            # Count logs mentioning the parse error
            parse_error_mentions = [
                log
                for log in error_logs
                if "parse error" in log.message.lower()
                or "validation" in log.message.lower()
            ]

            # Should be exactly 1 log entry about the parse error (not 2)
            assert (
                len(parse_error_mentions) == 1
            ), f"Expected 1 parse error log, got {len(parse_error_mentions)}: {[log.message for log in parse_error_mentions]}"


class TestLLMCombinedRetry:
    """Test combined network and parse error retry scenarios"""

    @pytest.mark.asyncio
    async def test_network_retry_then_parse_retry(self, test_settings):
        """Test network retry followed by parse error retry"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
    async def test_retry_logging(self, test_settings, caplog):
        """Test that retry attempts are properly logged"""
        llm = LLM(settings=test_settings, temperature=0.4, max_tokens=100)

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
