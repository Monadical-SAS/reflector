"""
# Summary meeting notes

This script is used to generate a summary of a meeting notes transcript.
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from enum import Enum
from functools import partial

import jsonschema
import structlog
from reflector.llm.base import LLM
from transformers import AutoTokenizer

JSON_SCHEMA_LIST_STRING = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {"type": "string"},
}

JSON_SCHEMA_ACTION_ITEMS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "assigned_to": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
        "required": ["content"],
    },
}

JSON_SCHEMA_DECISIONS_OR_OPEN_QUESTIONS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"content": {"type": "string"}},
        "required": ["content"],
    },
}

JSON_SCHEMA_TRANSCRIPTION_TYPE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "transcription_type": {"type": "string", "enum": ["meeting", "podcast"]},
    },
    "required": ["transcription_type"],
}


class ItemType(Enum):
    ACTION_ITEM = "action-item"
    DECISION = "decision"
    OPEN_QUESTION = "open-question"


class TranscriptionType(Enum):
    MEETING = "meeting"
    PODCAST = "podcast"


class Messages:
    """
    Manage the LLM context for conversational messages, with roles (system, user, assistant).
    """

    def __init__(self, messages=None, model_name=None, tokenizer=None, logger=None):
        self.messages = messages or []
        self.model_name = model_name
        self.tokenizer = tokenizer
        self.logger = logger

    def set_model(self, model):
        self.model_name = model

    def set_logger(self, logger):
        self.logger = logger

    def copy(self):
        m = Messages(
            self.messages[:],
            model_name=self.model_name,
            tokenizer=self.tokenizer,
            logger=self.logger,
        )
        return m

    def add_system(self, content: str):
        self.add("system", content)
        self.print_content("SYSTEM", content)

    def add_user(self, content: str):
        self.add("user", content)
        self.print_content("USER", content)

    def add_assistant(self, content: str):
        self.add("assistant", content)
        self.print_content("ASSISTANT", content)

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_tokenizer(self):
        if not self.tokenizer:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        return self.tokenizer

    def count_tokens(self):
        tokenizer = self.get_tokenizer()
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(tokenizer.tokenize(message["content"]))
        return total_tokens

    def get_tokens_count(self, message):
        tokenizer = self.get_tokenizer()
        return len(tokenizer.tokenize(message))

    def print_content(self, role, content):
        if not self.logger:
            return
        for line in content.split("\n"):
            self.logger.info(f">> {role}: {line}")


class SummaryBuilder:
    def __init__(self, llm, filename: str | None = None, logger=None):
        self.transcript: str | None = None
        self.recap: str | None = None
        self.summaries: list[dict] = []
        self.subjects: list[str] = []
        self.items_action: list = []
        self.items_decision: list = []
        self.items_question: list = []
        self.transcription_type: TranscriptionType | None = None
        self.llm_instance: LLM = llm
        self.model_name: str = llm.model_name
        self.logger = logger or structlog.get_logger()
        self.m = Messages(model_name=self.model_name, logger=self.logger)
        if filename:
            self.read_transcript_from_file(filename)

    def read_transcript_from_file(self, filename):
        """
        Load a transcript from a text file.
        Must be formatted as:

            speaker: message
            speaker2: message2

        """
        with open(filename, "r", encoding="utf-8") as f:
            self.transcript = f.read().strip()

    def set_transcript(self, transcript: str):
        assert isinstance(transcript, str)
        self.transcript = transcript

    def set_llm_instance(self, llm):
        self.llm_instance = llm

    # ----------------------------------------------------------------------------
    # Participants
    # ----------------------------------------------------------------------------

    async def identify_participants(self):
        """
        From a transcript, try identify the participants.
        This might not give the best result without good diarization, but it's a start.
        They are appended at the end of the transcript, providing more context for the assistant.
        """

        self.logger.debug("--- identify_participants")

        m = Messages(model_name=self.model_name)
        m.add_system(
            "You are an advanced note-taking assistant."
            "You'll be given a transcript, and identify the participants."
        )
        m.add_user(
            f"# Transcript\n\n{self.transcript}\n\n"
            "---\n\n"
            "Please identify the participants in the conversation."
            "Each participant should only be listed once, even if they are mentionned multiple times in the conversation."
            "Participants are real people who are part of the conversation and the speakers."
            "You can put participants that are mentioned by name."
            "Do not put company name."
            "Ensure that no duplicate names are included."
            "Output the result in JSON format following the schema: "
            f"\n```json-schema\n{JSON_SCHEMA_LIST_STRING}\n```"
        )
        result = await self.llm(
            m,
            [
                self.validate_json,
                partial(self.validate_json_schema, JSON_SCHEMA_LIST_STRING),
            ],
        )

        # augment the transcript with the participants.
        participants = self.format_list_md(result)
        self.transcript += f"\n\n# Participants\n\n{participants}"

    # ----------------------------------------------------------------------------
    # Transcription identification
    # ----------------------------------------------------------------------------

    async def identify_transcription_type(self):
        """
        Identify the type of transcription: meeting or podcast.
        """

        self.logger.debug("--- identify transcription type")

        m = Messages(model_name=self.model_name, logger=self.logger)
        m.add_system(
            "You are an advanced assistant specialize to recognize the type of an audio transcription."
            "It could be a meeting or a podcast."
        )
        m.add_user(
            f"# Transcript\n\n{self.transcript}\n\n"
            "---\n\n"
            "Please identify the type of transcription (meeting or podcast). "
            "Output the result in JSON format following the schema:"
            f"\n```json-schema\n{JSON_SCHEMA_TRANSCRIPTION_TYPE}\n```"
        )
        result = await self.llm(
            m,
            [
                self.validate_json,
                partial(self.validate_json_schema, JSON_SCHEMA_TRANSCRIPTION_TYPE),
            ],
        )

        transcription_type = result["transcription_type"]
        self.transcription_type = TranscriptionType(transcription_type)

    # ----------------------------------------------------------------------------
    # Items
    # ----------------------------------------------------------------------------

    async def generate_items(
        self,
        search_action=False,
        search_decision=False,
        search_open_question=False,
    ):
        """
        Build a list of item about action, decision or question
        """
        # require key subjects
        if not self.subjects or not self.summaries:
            await self.generate_summary()

        self.logger.debug("--- items")

        self.items_action = []
        self.items_decision = []
        self.items_question = []

        item_types = []
        if search_action:
            item_types.append(ItemType.ACTION_ITEM)
        if search_decision:
            item_types.append(ItemType.DECISION)
        if search_open_question:
            item_types.append(ItemType.OPEN_QUESTION)

        ## Version asking everything in one go
        for item_type in item_types:
            if item_type == ItemType.ACTION_ITEM:
                json_schema = JSON_SCHEMA_ACTION_ITEMS
                items = self.items_action
                prompt_definition = (
                    "An action item is a specific, actionable task designed to achieve a concrete outcome;"
                    "An action item scope is narrow, focused on short-term execution; "
                    "An action item is generally assigned to a specific person or team. "
                    "An action item is NOT a decision, a question, or a general topic. "
                    "For example: 'Gary, please send the report by Friday.' is an action item."
                    "But: 'I though Gary was here today. Anyway, somebody need to do an analysis.' is not an action item."
                    "The field assigned_to must contain a valid participant or person mentionned in the transcript."
                )

            elif item_type == ItemType.DECISION:
                json_schema = JSON_SCHEMA_DECISIONS_OR_OPEN_QUESTIONS
                items = self.items_decision
                prompt_definition = (
                    "A decision defines a broad or strategic direction or course of action;"
                    "It's more about setting the framework, high-level goals, or vision for what needs to happen;"
                    "A decision scope often affect multiple areas of the organization, and it's more about long-term impact."
                )

            elif item_type == ItemType.OPEN_QUESTION:
                json_schema = JSON_SCHEMA_DECISIONS_OR_OPEN_QUESTIONS
                items = self.items_question
                prompt_definition = ""

            await self.build_items_type(
                items, item_type, json_schema, prompt_definition
            )

    async def build_items_type(
        self,
        items: list,
        item_type: ItemType,
        json_schema: dict,
        prompt_definition: str,
    ):
        m = Messages(model_name=self.model_name, logger=self.logger)
        m.add_system(
            "You are an advanced note-taking assistant."
            f"You'll be given a transcript, and identify {item_type}."
            + prompt_definition
        )

        if item_type in (ItemType.ACTION_ITEM, ItemType.DECISION):
            # for both action_items and decision, break down per subject
            for subject in self.subjects:
                # find the summary of the subject
                summary = ""
                for entry in self.summaries:
                    if entry["subject"] == subject:
                        summary = entry["summary"]
                        break

                m2 = m.copy()
                m2.add_user(
                    f"# Transcript\n\n{self.transcript}\n\n"
                    f"# Main subjects\n\n{self.format_list_md(self.subjects)}\n\n"
                    f"# Summary of {subject}\n\n{summary}\n\n"
                    "---\n\n"
                    f'What are the {item_type.value} only related to the main subject "{subject}" ? '
                    f"Make sure the {item_type.value} do not overlap with other subjects. "
                    "To recall: "
                    + prompt_definition
                    + "If there are none, just return an empty list. "
                    "The result must be a list following this format: "
                    f"\n```json-schema\n{json_schema}\n```"
                )
                result = await self.llm(
                    m2,
                    [
                        self.validate_json,
                        partial(self.validate_json_schema, json_schema),
                    ],
                )
                if not result:
                    self.logger.error(
                        f"Error: unable to identify {item_type.value} for {subject}"
                    )
                    continue
                else:
                    items.extend(result)

            # and for action-items and decision, we try do deduplicate
            items = await self.deduplicate_items(item_type, items)

        elif item_type == ItemType.OPEN_QUESTION:
            m2 = m.copy()
            m2.add_user(
                f"# Transcript\n\n{self.transcript}\n\n"
                "---\n\n"
                f"Identify the open questions unanswered during the meeting."
                "If there are none, just return an empty list. "
                "The result must be a list following this format:"
                f"\n```json-schema\n{json_schema}\n```"
            )
            result = await self.llm(
                m2,
                [
                    self.validate_json,
                    partial(self.validate_json_schema, json_schema),
                ],
            )
            if not result:
                self.logger.error("Error: unable to identify open questions")
            else:
                items.extend(result)

    async def deduplicate_items(self, item_type: ItemType, items: list):
        """
        Deduplicate items based on the transcript and the list of items gathered for all subjects
        """
        m = Messages(model_name=self.model_name, logger=self.logger)
        if item_type == ItemType.ACTION_ITEM:
            json_schema = JSON_SCHEMA_ACTION_ITEMS
        else:
            json_schema = JSON_SCHEMA_DECISIONS_OR_OPEN_QUESTIONS

        title = item_type.value.replace("_", " ")

        m.add_system(
            "You are an advanced assistant that correlate and consolidate information. "
            f"Another agent found a list of {title}. However the list may be redundant. "
            f"Your first step will be to give information about how theses {title} overlap. "
            "In a second time, the user will ask you to consolidate according to your finding. "
            f"Keep in mind that the same {title} can be written in different ways. "
        )

        md_items = []
        for item in items:
            assigned_to = ", ".join(item.get("assigned_to", []))
            content = item["content"]
            if assigned_to:
                text = f"- **{assigned_to}**: {content}"
            else:
                text = f"- {content}"
            md_items.append(text)

        md_text = "\n".join(md_items)

        m.add_user(
            f"# Transcript\n\n{self.transcript}\n\n"
            f"# {title}\n\n{md_text}\n\n--\n\n"
            f"Here is a list of {title} identified by another agent. "
            f"Some of the {title} seem to overlap or be redundant. "
            "How can you effectively group or merge them into more consise list?"
        )

        await self.llm(m)

        m.add_user(
            f"Consolidate the list of {title} according to your finding. "
            f"The list must be shorter or equal than the original list. "
            "Give the result using the following JSON schema:"
            f"\n```json-schema\n{json_schema}\n```"
        )

        result = await self.llm(
            m,
            [
                self.validate_json,
                partial(self.validate_json_schema, json_schema),
            ],
        )
        return result

    # ----------------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------------

    async def generate_summary(self, only_subjects=False):
        """
        This is the main function to build the summary.

        It actually share the context with the different steps (subjects, quick recap)
        which make it more sense to keep it in one function.

        The process is:
        - Extract the main subjects
        - Generate a summary for all the main subjects
        - Generate a quick recap
        """
        self.logger.debug("--- extract main subjects")

        m = Messages(model_name=self.model_name, logger=self.logger)
        m.add_system(
            (
                "You are an advanced transcription summarization assistant."
                "Your task is to summarize discussions by focusing only on the main ideas contributed by participants."
                # Prevent generating another transcription
                "Exclude direct quotes and unnecessary details."
                # Do not mention others participants just because they didn't contributed
                "Only include participant names if they actively contribute to the subject."
                # Prevent generation of summary with "no others participants contributed" etc
                "Keep summaries concise and focused on main subjects without adding conclusions such as 'no other participant contributed'. "
                # Avoid: In the discussion, they talked about...
                "Do not include contextual preface. "
                # Prevention to have too long summary
                "Summary should fit in a single paragraph. "
                # Using other pronouns that the participants or the group
                'Mention the participants or the group using "they".'
                # Avoid finishing the summary with "No conclusions were added by the summarizer"
                "Do not mention conclusion if there is no conclusion"
            )
        )
        m.add_user(
            f"# Transcript\n\n{self.transcript}\n\n"
            + (
                "\n\n---\n\n"
                "What are the main/key subjects discussed in this transcript ? "
                "Do not include direct quotes or unnecessary details. "
                "Be concise and focused on the main ideas. "
                "A subject briefly mentionned should not be included. "
                f"The result must follow the JSON schema: {JSON_SCHEMA_LIST_STRING}. "
            ),
        )

        # Note: Asking the model the key subject sometimes generate a lot of subjects
        # We need to consolidate them to avoid redundancy when it happen.
        m2 = m.copy()

        subjects = await self.llm(
            m2,
            [
                self.validate_json,
                partial(self.validate_json_schema, JSON_SCHEMA_LIST_STRING),
            ],
        )
        if subjects:
            self.subjects = subjects

        if len(self.subjects) > 6:
            # the model may bugged and generate a lot of subjects
            m.add_user(
                "No that may be too much. "
                "Consolidate the subjects and remove any redundancy. "
                "Keep the most importants. "
                "Remember that the same subject can be written in different ways. "
                "Do not consolidate subjects if they are worth keeping separate due to their importance or sensitivity. "
                f"The result must follow the JSON schema: {JSON_SCHEMA_LIST_STRING}. "
            )
            subjects = await self.llm(
                m2,
                [
                    self.validate_json,
                    partial(self.validate_json_schema, JSON_SCHEMA_LIST_STRING),
                ],
            )
            if subjects:
                self.subjects = subjects

        # Write manually the assistants response to remove the redundancy if case somethign happen
        m.add_assistant(self.format_list_md(self.subjects))

        if only_subjects:
            return

        summaries = []

        # ----------------------------------------------------------------------------
        # Summarize per subject
        # ----------------------------------------------------------------------------

        m2 = m.copy()
        for subject in subjects:
            m2 = m  # .copy()
            prompt = (
                f"Summarize the main subject: '{subject}'. "
                "Include only the main ideas contributed by participants. "
                "Do not include direct quotes or unnecessary details. "
                "Avoid introducing or restating the subject. "
                "Focus on the core arguments without minor details. "
                "Summarize in few sentences. "
            )
            m2.add_user(prompt)

            summary = await self.llm(m2)
            summaries.append(
                {
                    "subject": subject,
                    "summary": summary,
                }
            )

        self.summaries = summaries

        # ----------------------------------------------------------------------------
        # Quick recap
        # ----------------------------------------------------------------------------

        m3 = m  # .copy()
        m3.add_user(
            "Provide a quick recap of the meeting, that fit into a small to medium paragraph."
        )
        recap = await self.llm(m3)
        self.recap = recap

    # ----------------------------------------------------------------------------
    # Markdown
    # ----------------------------------------------------------------------------

    def as_markdown(self):
        lines = []
        if self.recap:
            lines.append("# Quick recap")
            lines.append("")
            lines.append(self.recap)
            lines.append("")

        if self.items_action:
            lines.append("# Actions")
            lines.append("")
            for action in self.items_action:
                assigned_to = ", ".join(action.get("assigned_to", []))
                content = action.get("content", "")
                line = "-"
                if assigned_to:
                    line += f" **{assigned_to}**:"
                line += f" {content}"
                lines.append(line)
            lines.append("")

        if self.items_decision:
            lines.append("")
            lines.append("# Decisions")
            for decision in self.items_decision:
                content = decision.get("content", "")
                lines.append(f"- {content}")
            lines.append("")

        if self.items_question:
            lines.append("")
            lines.append("# Open questions")
            for question in self.items_question:
                content = question.get("content", "")
                lines.append(f"- {content}")
            lines.append("")

        if self.summaries:
            lines.append("# Summary")
            lines.append("")
            for summary in self.summaries:
                lines.append(f"**{summary['subject']}**")
                lines.append(summary["summary"])
                lines.append("")
            lines.append("")

        return "\n".join(lines)

    # ----------------------------------------------------------------------------
    # Validation API
    # ----------------------------------------------------------------------------

    def validate_list(self, result: str):
        # does the list match 1. xxx\n2. xxx... ?
        lines = result.split("\n")
        firstline = lines[0].strip()

        if re.match(r"1\.\s.+", firstline):
            # strip the numbers of the list
            lines = [re.sub(r"^\d+\.\s", "", line).strip() for line in lines]
            return lines

        if re.match(r"- ", firstline):
            # strip the list markers
            lines = [re.sub(r"^- ", "", line).strip() for line in lines]
            return lines

        return result.split("\n")

    def validate_next_steps(self, result: str):
        if result.lower().startswith("no"):
            return None

        return result

    def validate_json(self, result):
        # if result startswith ```json, strip begin/end
        result = result.strip()

        # grab the json between ```json and ``` using regex if exist
        match = re.search(r"```json(.*?)```", result, re.DOTALL)
        if match:
            result = match.group(1).strip()

        # try parsing json
        try:
            return json.loads(result)
        except Exception:
            self.logger.error(f"Unable to parse JSON: {result}")
            return result.split("\n")

    def validate_json_schema(self, schema, result):
        try:
            jsonschema.validate(instance=result, schema=schema)
        except Exception as e:
            self.logger.exception(e)
            raise
        return result

    # ----------------------------------------------------------------------------
    # LLM API
    # ----------------------------------------------------------------------------

    async def llm(
        self,
        messages: Messages,
        validate_func=None,
        auto_append=True,
        max_retries=3,
    ):
        """
        Perform a completion using the LLM model.
        Automatically validate the result and retry maximum `max_retries` times if an error occurs.
        Append the result to the message context if `auto_append` is True.
        """

        self.logger.debug(
            f"--- messages ({len(messages.messages)} messages, "
            f"{messages.count_tokens()} tokens)"
        )

        if validate_func and not isinstance(validate_func, list):
            validate_func = [validate_func]

        while max_retries > 0:
            try:
                # do the llm completion
                result = result_validated = await self.completion(
                    messages.messages,
                    logger=self.logger,
                )
                self.logger.debug(f"--- result\n{result_validated}")

                # validate the result using the provided functions
                if validate_func:
                    for func in validate_func:
                        result_validated = func(result_validated)

                self.logger.debug(f"--- validated\n{result_validated}")

                # add the result to the message context as an assistant response
                # only if the response was not guided
                if auto_append:
                    messages.add_assistant(result)
                return result_validated
            except Exception as e:
                self.logger.error(f"Error: {e}")
                max_retries -= 1

    async def completion(self, messages: list, **kwargs) -> str:
        """
        Complete the messages using the LLM model.
        The request assume a /v1/chat/completions compatible endpoint.
        `messages` are a list of dict with `role` and `content` keys.
        """

        result = await self.llm_instance.completion(messages=messages, **kwargs)
        return result["choices"][0]["message"]["content"]

    def format_list_md(self, data: list):
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
        "--items",
        help="Generate a list of action items",
        action="store_true",
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
        llm = LLM.get_instance(model_name="NousResearch/Hermes-3-Llama-3.1-8B")
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

        # if no summary or items is asked, ask for everything
        if not args.summary and not args.items and not args.subjects:
            args.summary = True
            args.items = True

        await sm.identify_participants()
        await sm.identify_transcription_type()

        if args.summary:
            await sm.generate_summary()

        if sm.transcription_type == TranscriptionType.MEETING:
            if args.items:
                await sm.generate_items(
                    search_action=True,
                    search_decision=True,
                    search_open_question=True,
                )

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
