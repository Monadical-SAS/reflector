import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from reflector.llm import LLM
from reflector.settings import settings


class SimpleResponse(BaseModel):
    """Test response model"""

    title: str = Field(description="A title")
    summary: str = Field(description="A summary")


@pytest.mark.asyncio
async def test_llm_validation_error_logs_full_json(caplog):
    """Test that validation errors log the complete raw JSON response"""

    # Create a real LLM instance
    llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

    # Mock the program.acall to raise a ValidationError with truncated display
    invalid_json = """{
  "title": "Test Title",
  "summary": "This is a very long summary that would normally be truncated in the error message display",
  "extra_field": "This field shouldn't be here"
}
{
  "description": "Strange trailing content that makes the JSON invalid - this simulates the actual error from production"
}"""

    with (
        patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        patch("reflector.llm.TreeSummarize") as mock_summarize,
        caplog.at_level(logging.ERROR),
    ):
        # Mock the summarizer to return text
        mock_summarizer_instance = MagicMock()
        mock_summarizer_instance.aget_response = AsyncMock(
            return_value="Analysis result"
        )
        mock_summarize.return_value = mock_summarizer_instance

        # Mock the program to raise ValidationError when acall is invoked
        mock_program_instance = MagicMock()

        # Create a real ValidationError as Pydantic would
        try:
            SimpleResponse.model_validate_json(invalid_json)
        except ValidationError as real_error:
            # Use the actual ValidationError from Pydantic
            mock_program_instance.acall = AsyncMock(side_effect=real_error)

        mock_program_class.from_defaults.return_value = mock_program_instance

        # Test that ValidationError is raised and full JSON is logged
        with pytest.raises(ValidationError):
            await llm.get_structured_response(
                prompt="Test prompt",
                texts=["Test text"],
                output_cls=SimpleResponse,
            )

        # Verify the full JSON was logged (not truncated)
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        assert log_record.levelname == "ERROR"
        assert "SimpleResponse" in log_record.message
        assert "Full raw JSON output:" in log_record.message

        # Most importantly: verify the complete JSON is in the log
        assert "Strange trailing content" in log_record.message
        assert invalid_json in log_record.message


@pytest.mark.asyncio
async def test_llm_validation_error_without_input_field(caplog):
    """Test error handling when ValidationError doesn't have expected structure"""

    llm = LLM(settings=settings, temperature=0.4, max_tokens=100)

    with (
        patch("reflector.llm.LLMTextCompletionProgram") as mock_program_class,
        patch("reflector.llm.TreeSummarize") as mock_summarize,
        caplog.at_level(logging.ERROR),
    ):
        # Mock the summarizer
        mock_summarizer_instance = MagicMock()
        mock_summarizer_instance.aget_response = AsyncMock(
            return_value="Analysis result"
        )
        mock_summarize.return_value = mock_summarizer_instance

        # Create a ValidationError without the typical structure
        mock_program_instance = MagicMock()
        mock_program_instance.acall = AsyncMock(
            side_effect=ValidationError.from_exception_data(
                "SimpleResponse", [{"type": "missing", "loc": ("title",)}]
            )
        )
        mock_program_class.from_defaults.return_value = mock_program_instance

        # Test that error is logged even without input field
        with pytest.raises(ValidationError):
            await llm.get_structured_response(
                prompt="Test prompt",
                texts=["Test text"],
                output_cls=SimpleResponse,
            )

        # Should still log an error, just without the full JSON
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        assert log_record.levelname == "ERROR"
        assert "SimpleResponse" in log_record.message
        assert "Validation errors:" in log_record.message
