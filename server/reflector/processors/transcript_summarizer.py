from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary
from pathlib import Path
import json


class TranscriptSummarizerProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = Path

    def __init__(self, filename: Path, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename
        self.chunkcount = 0

    async def _push(self, data: TitleSummary):
        with open(self.filename, "a", encoding="utf8") as fd:
            fd.write(json.dumps(data))
        self.chunkcount += 1

    async def _flush(self):
        if self.chunkcount == 0:
            self.logger.warning("No summary to write")
            return
        self.logger.info(f"Writing to {self.filename}")
        await self.emit(self.filename)
