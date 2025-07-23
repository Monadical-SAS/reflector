from typing import Optional, TypeVar

from pydantic import BaseModel
from transformers import GenerationConfig


class TaskParams(BaseModel, arbitrary_types_allowed=True):
    instruct: str
    gen_cfg: Optional[GenerationConfig] = None
    gen_schema: Optional[dict] = None


T = TypeVar("T", bound="LLMTaskParams")


class LLMTaskParams:
    _registry = {}

    @classmethod
    def register(cls, task, klass) -> None:
        cls._registry[task] = klass

    @classmethod
    def get_instance(cls, task: str) -> T:
        return cls._registry[task]()

    @property
    def task_params(self) -> TaskParams | None:
        """
        Fetch the task related parameters
        """
        return self._get_task_params()

    def _get_task_params(self) -> None:
        pass


class FinalLongSummaryParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=1000, num_beams=3, do_sample=True, temperature=0.3
        )
        self._instruct = """
        Take the key ideas and takeaways from the text and create a short
         summary. Be sure to keep the length of the response to a minimum.
         Do not include trivial information in the summary.
          """
        self._schema = {
            "type": "object",
            "properties": {"long_summary": {"type": "string"}},
        }
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=self._schema, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """gen_schema
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


class FinalShortSummaryParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=800, num_beams=3, do_sample=True, temperature=0.3
        )
        self._instruct = """
        Take the key ideas and takeaways from the text and create a short
         summary. Be sure to keep the length of the response to a minimum.
         Do not include trivial information in the summary.
          """
        self._schema = {
            "type": "object",
            "properties": {"short_summary": {"type": "string"}},
        }
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=self._schema, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


class FinalTitleParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=200, num_beams=5, do_sample=True, temperature=0.5
        )
        self._instruct = """
            Combine the following individual titles into one single short title that
            condenses the essence of all titles.
        """
        self._schema = {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=self._schema, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


class TopicParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=500, num_beams=6, do_sample=True, temperature=0.9
        )
        self._instruct = """
                Create a JSON object as response.The JSON object must have 2 fields:
                i) title and ii) summary.
                For the title field, generate a very detailed and self-explanatory
                 title for the given text. Let the title be as descriptive as possible.
                Use nominalization - convert sentences into noun phrases (e.g., instead of 
                "The team discussed deadlines" use "Team deadline discussion").
                For the summary field, summarize the given text in a maximum of
                two sentences.
            """
        self._schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
        }
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=self._schema, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


class BulletedSummaryParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=800,
            num_beams=1,
            do_sample=True,
            temperature=0.2,
            early_stopping=True,
        )
        self._instruct = """
        Given a meeting transcript, extract the key things discussed in the
         form of a list.

        While generating the response, follow the constraints mentioned below.

        Summary constraints:
        i) Do not add new content, except to fix spelling or punctuation.
        ii) Do not add any prefixes or numbering in the response.
        iii) The summarization should be as information dense as possible.
        iv) Do not add any additional sections like Note, Conclusion, etc. in
        the response.

        Response format:
        i) The response should be in the form of a bulleted list.
        ii) Iteratively merge all the relevant paragraphs together to keep the
         number of paragraphs to a minimum.
        iii) Remove any unfinished sentences from the final response.
        iv) Do not include narrative or reporting clauses.
        v) Use "*" as the bullet icon.
    """
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=None, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """gen_schema
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


class MergedSummaryParams(LLMTaskParams):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gen_cfg = GenerationConfig(
            max_new_tokens=600,
            num_beams=1,
            do_sample=True,
            temperature=0.2,
            early_stopping=True,
        )
        self._instruct = """
        Given the key points of a meeting, summarize the points to describe the
         meeting in the form of paragraphs.
        """
        self._task_params = TaskParams(
            instruct=self._instruct, gen_schema=None, gen_cfg=self._gen_cfg
        )

    def _get_task_params(self) -> TaskParams:
        """gen_schema
        Return the parameters associated with a specific LLM task
        """
        return self._task_params


LLMTaskParams.register("topic", TopicParams)
LLMTaskParams.register("final_title", FinalTitleParams)
LLMTaskParams.register("final_short_summary", FinalShortSummaryParams)
LLMTaskParams.register("final_long_summary", FinalLongSummaryParams)
LLMTaskParams.register("bullet_summary", BulletedSummaryParams)
LLMTaskParams.register("merged_summary", MergedSummaryParams)
