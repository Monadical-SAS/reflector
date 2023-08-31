from transformers import GenerationConfig


class LLMParams:
    task = ""
    generation_configs = {
        "topic": GenerationConfig(
            max_new_tokens=300, num_beams=3, use_cache=True, temperature=0.9
        ),
        "title": GenerationConfig(
            max_new_tokens=200, num_beams=5, use_cache=True, temperature=0.5
        ),
        "summary": GenerationConfig(
            max_new_tokens=1300, num_beams=3, use_cache=True, temperature=0.3
        ),
    }
    schemas = {
        "topic": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
        },
        "title": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        },
        "summary": {"type": "object", "properties": {"summary": {"type": "string"}}},
    }
    instructs = {
        "topic": """
                Create a JSON object as response.The JSON object must have 2 fields:
                i) title and ii) summary.
                For the title field, generate a short title for the given text.
                For the summary field, summarize the given text in a maximum of
                three sentences.
            """,
        "title": """
                Combine the following individual titles into one single short title that
                condenses the essence of all titles.
            """,
        "summary": """
                Take the key ideas and takeaways from the text and create a short
                 summary. Be sure to keep the length of the response to a minimum.
                Do not include trivial information in the summary.
            """,
    }

    def __init__(self, task):
        self.task = task

    @property
    def gen_cfg(self):
        if self.task in self.generation_configs:
            return self.generation_configs[self.task]

    @property
    def schema(self):
        if self.task in self.schemas:
            return self.schemas[self.task]

    @property
    def instruct(self):
        return self.instructs[self.task]
