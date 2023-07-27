"""
Collection of data classes for streamlining and rigidly structuring
the input and output parameters of functions
"""

import datetime
from dataclasses import dataclass
from typing import List

import av


@dataclass
class TitleSummaryInput:
    """
    Data class for the input to generate title and summaries.
    The outcome will be used to send query to the LLM for processing.
    """
    input_text = str
    transcribed_time = float
    prompt = str
    data = dict

    def __init__(self, transcribed_time, input_text=""):
        self.input_text = input_text
        self.transcribed_time = transcribed_time
        self.prompt = \
            f"""
            ### Human:
            Create a JSON object as response.The JSON object must have 2 fields:
            i) title and ii) summary.For the title field,generate a short title
            for the given text. For the summary field, summarize the given text
            in three sentences.

            {self.input_text}

            ### Assistant:
            """
        self.data = {"prompt": self.prompt}
        self.headers = {"Content-Type": "application/json"}


@dataclass
class IncrementalResult:
    """
    Data class for the result of generating one title and summaries.
    Defines how a single "topic" looks like.
    """
    title = str
    description = str
    transcript = str
    timestamp = str

    def __init__(self, title, desc, transcript, timestamp):
        self.title = title
        self.description = desc
        self.transcript = transcript
        self.timestamp = timestamp


@dataclass
class TitleSummaryOutput:
    """
    Data class for the result of all generated titles and summaries.
    The result will be sent back to the client
    """
    cmd = str
    topics = List[IncrementalResult]

    def __init__(self, inc_responses):
        self.topics = inc_responses
        self.cmd = "UPDATE_TOPICS"

    def get_result(self) -> dict:
        """
        Return the result dict for displaying the transcription
        :return:
        """
        return {
                "cmd": self.cmd,
                "topics": self.topics
        }


@dataclass
class ParseLLMResult:
    """
    Data class to parse the result returned by the LLM while generating title
    and summaries. The result will be sent back to the client.
    """
    title = str
    description = str
    transcript = str
    timestamp = str

    def __init__(self, param: TitleSummaryInput, output: dict):
        self.title = output["title"]
        self.transcript = param.input_text
        self.description = output.pop("summary")
        self.timestamp = \
            str(datetime.timedelta(seconds=round(param.transcribed_time)))

    def get_result(self) -> dict:
        """
        Return the result dict after parsing the response from LLM
        :return:
        """
        return {
                "title": self.title,
                "description": self.description,
                "transcript": self.transcript,
                "timestamp": self.timestamp
        }


@dataclass
class TranscriptionInput:
    """
    Data class to define the input to the transcription function
    AudioFrames -> input
    """
    frames = List[av.audio.frame.AudioFrame]

    def __init__(self, frames):
        self.frames = frames


@dataclass
class TranscriptionOutput:
    """
    Dataclass to define the result of the transcription function.
    The result will be sent back to the client
    """
    cmd = str
    result_text = str

    def __init__(self, result_text):
        self.cmd = "SHOW_TRANSCRIPTION"
        self.result_text = result_text

    def get_result(self) -> dict:
        """
        Return the result dict for displaying the transcription
        :return:
        """
        return {
                "cmd": self.cmd,
                "text": self.result_text
        }


@dataclass
class FinalSummaryResult:
    """
    Dataclass to define the result of the final summary function.
    The result will be sent back to the client.
    """
    cmd = str
    final_summary = str
    duration = str

    def __init__(self, final_summary, time):
        self.duration = str(datetime.timedelta(seconds=round(time)))
        self.final_summary = final_summary
        self.cmd = "DISPLAY_FINAL_SUMMARY"

    def get_result(self) -> dict:
        """
        Return the result dict for displaying the final summary
        :return:
        """
        return {
                "cmd": self.cmd,
                "duration": self.duration,
                "summary": self.final_summary
        }


class BlackListedMessages:
    """
    Class to hold the blacklisted messages. These messages should be filtered
    out and not sent back to the client as part of the transcription.
    """
    messages = [" Thank you.", " See you next time!",
                " Thank you for watching!", " Bye!",
                " And that's what I'm talking about."]
