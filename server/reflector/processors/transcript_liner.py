from reflector.processors.base import Processor
from reflector.processors.types import Transcript


class TranscriptLinerProcessor(Processor):
    """
    Based on stream of transcript, assemble and remove duplicated words
    then cut per lines.
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = Transcript

    def __init__(self, max_text=1000, **kwargs):
        super().__init__(**kwargs)
        self.transcript = Transcript(words=[])
        self.max_text = max_text

    async def _push(self, data: Transcript):
        # merge both transcript
        self.transcript.merge(data)

        # check if a line is complete
        if "." not in self.transcript.text:
            # if the transcription text is still not too long, wait for more
            if len(self.transcript.text) < self.max_text:
                return

        # cut to the next .
        partial = Transcript(words=[])
        for word in self.transcript.words[:]:
            partial.text += word.text
            partial.words.append(word)
            if "." not in word.text:
                continue

            partial.translation = self.transcript.translation
            # emit line
            await self.emit(partial)

            # create new transcript
            partial = Transcript(words=[])
        self.transcript = partial

    async def _flush(self):
        if self.transcript.words:
            await self.emit(self.transcript)
