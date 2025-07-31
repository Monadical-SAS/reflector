"""
# Summary meeting notes

This script is used to generate a summary of a meeting notes transcript.
"""

import asyncio
import sys
from datetime import datetime
from enum import Enum

import structlog
from llama_index.core import Settings
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel, Field
from reflector.llm.base import LLM
from reflector.llm.openai_llm import OpenAILLM
from reflector.settings import settings


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
        max_items=6,
    )


class SummaryBuilder:
    def __init__(self, llm: LLM, filename: str | None = None, logger=None) -> None:
        self.transcript: str | None = None
        self.recap: str | None = None
        self.summaries: list[dict[str, str]] = []
        self.subjects: list[str] = []
        self.transcription_type: TranscriptionType | None = None
        self.llm_instance: LLM = llm
        self.model_name: str = llm.model_name
        self.logger = logger or structlog.get_logger()
        if filename:
            self.read_transcript_from_file(filename)

        Settings.llm = OpenAILike(
            model=llm.model_name,
            api_base=llm.url,
            api_key=llm.api_key,
            context_window=settings.SUMMARY_LLM_CONTEXT_SIZE_TOKENS,
            is_chat_model=True,
            is_function_calling_model=False,
            temperature=llm.temperature,
            max_tokens=llm.max_tokens,
        )

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
        self.llm_instance = llm

    async def _get_structured_response(
        self, prompt: str, output_cls: type[BaseModel], tone_name: str | None = None
    ) -> BaseModel:
        """Generic function to get structured output from LLM for non-function-calling models."""
        from llama_index.core.output_parsers import PydanticOutputParser
        from llama_index.core.program import LLMTextCompletionProgram

        # First, use TreeSummarize to get the response
        summarizer = TreeSummarize(verbose=True)

        response = await summarizer.aget_response(
            prompt, [self.transcript], tone_name=tone_name
        )

        # Then, use PydanticOutputParser to structure the response
        output_parser = PydanticOutputParser(output_cls)

        prompt_template_str = """Based on the following analysis, provide the information in the requested JSON format:

Analysis:
{analysis}

{format_instructions}"""

        program = LLMTextCompletionProgram.from_defaults(
            output_parser=output_parser,
            prompt_template_str=prompt_template_str,
            verbose=False,
        )

        format_instructions = output_parser.format(
            "Please structure the above information in the following JSON format:"
        )

        output = await program.acall(
            analysis=str(response), format_instructions=format_instructions
        )

        return output

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

        participants_prompt = (
            "Identify all participants in this conversation.\n"
            "Distinguish between people who actually spoke in the transcript and those who were only mentioned.\n"
            "Each participant should only be listed once.\n"
            "Do not include company names, only people's names."
        )

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

            unique_participants = all_participants + response.mentioned_only

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

        transcription_type_prompt = (
            "Analyze this transcript and determine if it is a meeting, podcast, or interview.\n"
            "A meeting typically has multiple participants discussing topics, making decisions, and planning actions.\n"
            "A podcast typically has hosts discussing topics or interviewing guests in a structured format for an audience.\n"
            "An interview typically has an interviewer asking questions to one or more interviewees, often for hiring, research, or journalism purposes.\n"
            "Provide your classification with confidence score and reasoning."
        )

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

        subjects_prompt = (
            "What are the main / high level topic of the meeting. "
            "Do not include direct quotes or unnecessary details. "
            "Be concise and focused on the main ideas. "
            "A subject briefly mentioned should not be included. "
            "There should be maximum 6 subjects. "
            "Do not write complete narrative sentences for the subject, "
            "you must write a concise subject using noun phrases."
        )

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
        summarizer = TreeSummarize(verbose=True)
        summaries = []

        for subject in self.subjects:
            detailed_prompt = f"""
Get me information about the topic "{subject}"

#RESPONSE GUIDELINES
Follow this structured approach to create the topic summary:
- Highlight any important arguments, insights or data presented.
- Outline decisions made.
- Indicate any decisions that were reached, including any rational or key
factors that influenced theses decisions.
- Detail action items and responsabilities.
- For each decision or unresolved issue, list out the specific action
items that were agreed upon, along with the assigned individuals or
teams responsible for each task.
- Specify deadlines or timelines if talked about. For each action item,
include any deadlines or timeframes discussed for completions or follow-up.
- Mention any unresolved issues or topics that need further discussion.
This help in planning future meetings or follow-up actions.

#OUTPUT
Your summary should be clear, concise, and structured, covering all the
major points, decisions, and action items from the meeting.
It should be easily understandable to someone who wasn't present, giving
them a comprehensive understanding of what transpired and what needs to
be done next. The summary should not exceed one page to ensure brevity
and focus.
"""

            detailed_response = await summarizer.aget_response(
                detailed_prompt, [self.transcript], tone_name="Topic assistant"
            )

            paragraph_prompt = (
                "Summarize the mentioned topic in 1 paragraph.\n"
                "It will be integrated into the final summary, so just for this topic.\n\n"
            )

            paragraph_response = await summarizer.aget_response(
                paragraph_prompt, [str(detailed_response)], tone_name="Topic summarizer"
            )

            summaries.append({"subject": subject, "summary": str(paragraph_response)})
            self.logger.debug(f"Summary for {subject}: {paragraph_response}")

        self.summaries = summaries

    async def generate_recap(self) -> None:
        """Generate a quick recap from the subject summaries."""
        summarizer = TreeSummarize(verbose=True)

        summaries_text = "\n\n".join(
            [
                f"{summary['subject']}: {summary['summary']}"
                for summary in self.summaries
            ]
        )

        recap_prompt = (
            "Provide a high-level quick recap of the following meeting, fitting in one paragraph.\n"
            "Do not include decisions, action items or unresolved issue, just highlight the high moments.\n"
            "Just dive into the meeting, be concise and do not include unnecessary details.\n"
            "As we know it is a meeting, do not start with 'During the meeting' or equivalent.\n\n"
        )

        recap_response = await summarizer.aget_response(
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

        llm = OpenAILLM(config_prefix="SUMMARY", settings=settings)
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
