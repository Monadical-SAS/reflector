import datetime
from dataclasses import dataclass
from typing import List

import av


@dataclass
class TitleSummaryInput:
    input_text = str
    transcribed_time = float
    prompt = str
    data = dict

    def __init__(self, transcribed_time, input_text=""):
        self.input_text = input_text
        self.transcribed_time = transcribed_time
        self.prompt = f"""
                    ### Human:
                    Create a JSON object as response. The JSON object must have 2 fields:
                    i) title and ii) summary. For the title field,generate a short title
                    for the given text. For the summary field, summarize the given text
                    in three sentences.

                    {self.input_text}

                    ### Assistant:
                    """
        self.data = {"data": self.prompt}
        self.headers = {"Content-Type": "application/json"}


@dataclass
class IncrementalResponse:
    title = str
    description = str
    transcript = str

    def __init__(self, title, desc, transcript):
        self.title = title
        self.description = desc
        self.transcript = transcript


@dataclass
class TitleSummaryOutput:
    cmd = str
    topics = List[IncrementalResponse]

    def __init__(self, inc_responses):
        self.topics = inc_responses

    def get_response(self):
        return {
                "cmd": self.cmd,
                "topics": self.topics
        }


@dataclass
class ParseLLMResult:
    description = str
    transcript = str
    timestamp = str

    def __init__(self, param: TitleSummaryInput, output: dict):
        self.transcript = param.input_text
        self.description = output.pop("summary")
        self.timestamp = str(datetime.timedelta(seconds=round(param.transcribed_time)))

    def get_result(self):
        return {
                "description": self.description,
                "transcript": self.transcript,
                "timestamp": self.timestamp
        }


@dataclass
class TranscriptionInput:
    frames = List[av.audio.frame.AudioFrame]

    def __init__(self, frames):
        self.frames = frames


@dataclass
class TranscriptionOutput:
    cmd = str
    result_text = str

    def __init__(self, result_text):
        self.cmd = "SHOW_TRANSCRIPTION"
        self.result_text = result_text

    def get_response(self):
        return {
                "cmd": self.cmd,
                "text": self.result_text
        }


@dataclass
class FinalSummaryResponse:
    cmd = str
    final_summary = str
    duration = str

    def __init__(self, final_summary, time):
        self.duration = str(datetime.timedelta(seconds=round(time)))
        self.final_summary = final_summary
        self.cmd = ""

    def get_response(self):
        return {
                "cmd": self.cmd,
                "duration": self.duration,
                "summary": self.final_summary
        }
