"""
# Summary meeting notes

This script is used to generate a summary of a meeting notes transcript.
"""

import asyncio
import sys
from datetime import datetime
from enum import Enum
from textwrap import dedent
from typing import Type, TypeVar

import structlog
from pydantic import BaseModel, Field

from reflector.llm import LLM
from reflector.settings import settings

T = TypeVar("T", bound=BaseModel)

PARTICIPANTS_PROMPT = dedent(
    """
    Identify all participants in this conversation.
    Distinguish between people who actually spoke in the transcript and those who were only mentioned.
    Each participant should only be listed once.
    Do not include company names, only people's names.
    """
).strip()

TRANSCRIPTION_TYPE_PROMPT = dedent(
    """
    Analyze the transcript to determine if it is a meeting, podcast, or interview.
    A meeting typically involves severals participants engaging in discussions,
    making decisions, and planning actions. A podcast often includes hosts
    discussing topics or interviewing guests for an audience in a structured format.
    An interview generally features one or more interviewer questioning one or
    more interviewees, often for hiring, research, or journalism. Deliver your
    classification with a confidence score and reasoning.
    """
).strip()

SUBJECTS_PROMPT = dedent(
    """
    What are the main / high level topic of the meeting.
    Do not include direct quotes or unnecessary details.
    Be concise and focused on the main ideas.
    A subject briefly mentioned should not be included.
    There should be maximum 6 subjects.
    Do not write complete narrative sentences for the subject,
    you must write a concise subject using noun phrases.
    """
).strip()

DETAILED_SUBJECT_PROMPT_TEMPLATE = dedent(
    """
    Get me information about the topic "{subject}"

    # RESPONSE GUIDELINES
    Follow this structured approach to create the topic summary:
    - Highlight important arguments, insights, or data presented.
    - Outline decisions made.
    - Indicate any decisions reached, including any rationale or key factors
      that influenced these decisions.
    - Detail action items and responsibilities.
    - For each decision or unresolved issue, list specific action items agreed
      upon, along with assigned individuals or teams responsible for each task.
    - Specify deadlines or timelines if mentioned. For each action item,
      include any deadlines or timeframes discussed for completion or follow-up.
    - Mention unresolved issues or topics needing further discussion, aiding in
      planning future meetings or follow-up actions.
    - Do not include topic unrelated to {subject}.

    # OUTPUT
    Your summary should be clear, concise, and structured, covering all major
    points, decisions, and action items from the meeting. It should be easy to
    understand for someone not present, providing a comprehensive understanding
    of what transpired and what needs to be done next. The summary should not
    exceed one page to ensure brevity and focus.
    """
).strip()

PARAGRAPH_SUMMARY_PROMPT = dedent(
    """
    Summarize the mentioned topic in 1 paragraph.
    It will be integrated into the final summary, so just for this topic.
    """
).strip()

RECAP_PROMPT = dedent(
    """
    Provide a high-level quick recap of the following meeting, fitting in one paragraph.
    Do not include decisions, action items or unresolved issue, just highlight the high moments.
    Just dive into the meeting, be concise and do not include unnecessary details.
    As we already know it is a meeting, do not start with 'During the meeting' or equivalent.
    """
).strip()

STRUCTURED_RESPONSE_PROMPT_TEMPLATE = dedent(
    """
    Based on the following analysis, provide the information in the requested JSON format:

    Analysis:
    {analysis}

    {format_instructions}
    """
).strip()


class TranscriptionType(Enum):
    MEETING = "meeting"
    PODCAST = "podcast"
    INTERVIEW = "interview"


class TranscriptionTypeResponse(BaseModel):
    """Pydantic model for transcription type classification"""

    transcription_type: str = Field(
        description="The type of transcription - either 'meeting', 'podcast', or 'interview'"
    )
    confidence: float = Field(
        description="Confidence score between 0 and 1", ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Brief explanation for the classification")


class ParticipantInfo(BaseModel):
    """Information about a single participant"""

    name: str = Field(description="The name of the participant")
    is_speaker: bool = Field(
        default=True, description="Whether this person spoke in the transcript"
    )


class ParticipantsResponse(BaseModel):
    """Pydantic model for participants identification"""

    participants: list[ParticipantInfo] = Field(
        description="List of all participants in the conversation"
    )
    total_speakers: int = Field(description="Total number of people who spoke")
    mentioned_only: list[str] = Field(
        default_factory=list, description="Names mentioned but who didn't speak"
    )


class SubjectsResponse(BaseModel):
    """Pydantic model for extracted subjects/topics"""

    subjects: list[str] = Field(
        description="List of main subjects/topics discussed, maximum 6 items",
    )


class SummaryBuilder:
    def __init__(self, llm: LLM, filename: str | None = None, logger=None) -> None:
        self.transcript: str | None = None
        self.recap: str | None = None
        self.summaries: list[dict[str, str]] = []
        self.subjects: list[str] = []
        self.transcription_type: TranscriptionType | None = None
        self.llm: LLM = llm
        self.model_name: str = llm.model_name
        self.logger = logger or structlog.get_logger()
        if filename:
            self.read_transcript_from_file(filename)

    def read_transcript_from_file(self, filename: str) -> None:
        """
        Load a transcript from a text file.
        Must be formatted as:

            speaker: message
            speaker2: message2

        """
        with open(filename, "r", encoding="utf-8") as f:
            self.transcript = f.read().strip()

    def set_transcript(self, transcript: str) -> None:
        assert isinstance(transcript, str)
        self.transcript = transcript

    def set_llm_instance(self, llm: LLM) -> None:
        self.llm = llm

    async def _get_structured_response(
        self, prompt: str, output_cls: Type[T], tone_name: str | None = None
    ) -> Type[T]:
        """Generic function to get structured output from LLM for non-function-calling models."""
        return await self.llm.get_structured_response(
            prompt, [self.transcript], output_cls, tone_name=tone_name
        )

    # ----------------------------------------------------------------------------
    # Participants
    # ----------------------------------------------------------------------------

    async def identify_participants(self) -> None:
        """
        From a transcript, try to identify the participants using TreeSummarize with structured output.
        This might not give the best result without good diarization, but it's a start.
        They are appended at the end of the transcript, providing more context for the assistant.
        """

        self.logger.debug("--- identify_participants using TreeSummarize with Pydantic")

        participants_prompt = PARTICIPANTS_PROMPT

        try:
            response = await self._get_structured_response(
                participants_prompt,
                ParticipantsResponse,
                tone_name="Participant identifier",
            )

            all_participants = [p.name for p in response.participants]

            self.logger.info(
                "Participants analysis complete",
                total_speakers=response.total_speakers,
                speakers=[p.name for p in response.participants if p.is_speaker],
                mentioned_only=response.mentioned_only,
                total_identified=len(all_participants) + len(response.mentioned_only),
            )

            unique_participants = list(set(all_participants + response.mentioned_only))

            if unique_participants:
                participants_md = self.format_list_md(unique_participants)
                self.transcript += f"\n\n# Participants\n\n{participants_md}"
            else:
                self.logger.warning("No participants identified in the transcript")

        except Exception as e:
            self.logger.error(f"Error in participant identification: {e}")
            self.logger.warning(
                "Failed to identify participants, continuing without them"
            )

    # ----------------------------------------------------------------------------
    # Transcription identification
    # ----------------------------------------------------------------------------

    async def identify_transcription_type(self) -> None:
        """
        Identify the type of transcription: meeting or podcast using TreeSummarizer with structured output.
        """

        self.logger.debug(
            "--- identify transcription type using TreeSummarizer with Pydantic"
        )

        transcription_type_prompt = TRANSCRIPTION_TYPE_PROMPT

        try:
            response = await self._get_structured_response(
                transcription_type_prompt,
                TranscriptionTypeResponse,
                tone_name="Transcription type classifier",
            )

            self.logger.info(
                f"Transcription type identified: {response.transcription_type} "
                f"(confidence: {response.confidence:.2f})"
            )
            self.logger.debug(f"Reasoning: {response.reasoning}")

            if response.transcription_type.lower() == "meeting":
                self.transcription_type = TranscriptionType.MEETING
            elif response.transcription_type.lower() == "podcast":
                self.transcription_type = TranscriptionType.PODCAST
            elif response.transcription_type.lower() == "interview":
                self.transcription_type = TranscriptionType.INTERVIEW
            else:
                self.logger.warning(
                    f"Unexpected transcription type: {response.transcription_type}, "
                    f"defaulting to meeting"
                )
                self.transcription_type = TranscriptionType.MEETING

        except Exception as e:
            self.logger.error(f"Error in transcription type identification: {e}")
            self.transcription_type = TranscriptionType.MEETING

    # ----------------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------------

    async def extract_subjects(self) -> None:
        """Extract main subjects/topics from the transcript."""
        self.logger.info("--- extract main subjects using TreeSummarize")

        subjects_prompt = SUBJECTS_PROMPT

        try:
            response = await self._get_structured_response(
                subjects_prompt,
                SubjectsResponse,
                tone_name="Meeting assistant that talk only as list item",
            )

            self.subjects = response.subjects
            self.logger.info(f"Extracted subjects: {self.subjects}")

        except Exception as e:
            self.logger.error(f"Error extracting subjects: {e}")
            self.subjects = []

    async def generate_subject_summaries(self) -> None:
        """Generate detailed summaries for each extracted subject."""
        assert self.transcript is not None
        summaries = []

        for subject in self.subjects:
            detailed_prompt = DETAILED_SUBJECT_PROMPT_TEMPLATE.format(subject=subject)

            detailed_response = await self.llm.get_response(
                detailed_prompt, [self.transcript], tone_name="Topic assistant"
            )

            paragraph_prompt = PARAGRAPH_SUMMARY_PROMPT

            paragraph_response = await self.llm.get_response(
                paragraph_prompt, [str(detailed_response)], tone_name="Topic summarizer"
            )

            summaries.append({"subject": subject, "summary": str(paragraph_response)})
            self.logger.debug(f"Summary for {subject}: {paragraph_response}")

        self.summaries = summaries

    async def generate_recap(self) -> None:
        """Generate a quick recap from the subject summaries."""

        summaries_text = "\n\n".join(
            [
                f"{summary['subject']}: {summary['summary']}"
                for summary in self.summaries
            ]
        )

        recap_prompt = RECAP_PROMPT

        recap_response = await self.llm.get_response(
            recap_prompt, [summaries_text], tone_name="Recap summarizer"
        )

        self.recap = str(recap_response)
        self.logger.info(f"Quick recap: {self.recap}")

    async def generate_summary(self, only_subjects: bool = False) -> None:
        """
        Generate summary by extracting subjects, creating summaries for each, and generating a recap.
        """
        await self.extract_subjects()

        if only_subjects:
            return

        await self.generate_subject_summaries()
        await self.generate_recap()

    # ----------------------------------------------------------------------------
    # Markdown
    # ----------------------------------------------------------------------------

    def as_markdown(self) -> str:
        lines: list[str] = []
        if self.recap:
            lines.append("# Quick recap")
            lines.append("")
            lines.append(self.recap)
            lines.append("")

        if self.summaries:
            lines.append("# Summary")
            lines.append("")
            for summary in self.summaries:
                lines.append(f"**{summary['subject']}**")
                lines.append(summary["summary"])
                lines.append("")

        return "\n".join(lines)

    def format_list_md(self, data: list[str]) -> str:
        return "\n".join([f"- {item}" for item in data])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a summary of a meeting transcript"
    )

    parser.add_argument(
        "transcript",
        type=str,
        nargs="?",
        help="The transcript of the meeting",
        default="transcript.txt",
    )

    parser.add_argument(
        "--transcription-type",
        action="store_true",
        help="Identify the type of the transcript (meeting, interview, podcast...)",
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the summary to a file",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a summary",
    )

    parser.add_argument(
        "--subjects",
        help="Generate a list of subjects",
        action="store_true",
    )

    parser.add_argument(
        "--participants",
        help="Generate a list of participants",
        action="store_true",
    )

    args = parser.parse_args()

    async def main():
        # build the summary

        llm = LLM(settings=settings)
        sm = SummaryBuilder(llm=llm, filename=args.transcript)

        if args.subjects:
            await sm.generate_summary(only_subjects=True)
            print("# Subjects\n")
            print("\n".join(sm.subjects))
            sys.exit(0)

        if args.transcription_type:
            await sm.identify_transcription_type()
            print(sm.transcription_type)
            sys.exit(0)

        if args.participants:
            await sm.identify_participants()
            sys.exit(0)

        # if no summary is asked, ask for everything
        if not args.summary and not args.subjects:
            args.summary = True

        if args.summary:
            await sm.generate_summary()

        # Note: action items generation has been removed

        print("")
        print("-" * 80)
        print("")
        print(sm.as_markdown())

        if args.save:
            # write the summary to a file, on the format summary-<iso date>.md
            filename = f"summary-{datetime.now().isoformat()}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(sm.as_markdown())

            print("")
            print("-" * 80)
            print("")
            print("Saved to", filename)

    asyncio.run(main())
