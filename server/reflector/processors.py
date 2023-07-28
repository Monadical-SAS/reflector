from pathlib import Path
import av
import wave
from dataclasses import dataclass
from faster_whisper import WhisperModel
from reflector.models import TitleSummaryInput, ParseLLMResult
from reflector.settings import settings
from reflector.logger import logger
import httpx
import asyncio
from concurrent.futures import ThreadPoolExecutor


@dataclass
class AudioFile:
    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: float = 0.0


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class TitleSummary:
    title: str
    summary: str


@dataclass
class Transcript:
    text: str = ""
    words: list[Word] = None

    @property
    def human_timestamp(self):
        minutes = int(self.timestamp / 60)
        seconds = int(self.timestamp % 60)
        milliseconds = int((self.timestamp % 1) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @property
    def timestamp(self):
        if not self.words:
            raise ValueError("No words in transcript")
        return self.words[0].start

    @property
    def duration(self):
        if not self.words:
            raise ValueError("No words in transcript")
        return self.words[-1].end - self.words[0].start

    def merge(self, other: "Transcript"):
        if not self.words:
            self.words = other.words
        else:
            self.words.extend(other.words)
        self.text += other.text


class Processor:
    INPUT_TYPE: type = None
    OUTPUT_TYPE: type = None

    def __init__(self):
        self._processors = []
        self._callbacks = []

    def connect(self, processor: "Processor"):
        if processor.INPUT_TYPE != self.OUTPUT_TYPE:
            raise ValueError(
                f"Processor {processor} input type {processor.INPUT_TYPE} "
                f"does not match {self.OUTPUT_TYPE}"
            )
        self._processors.append(processor)

    def disconnect(self, processor: "Processor"):
        self._processors.remove(processor)

    def on(self, callback):
        self._callbacks.append(callback)

    def off(self, callback):
        self._callbacks.remove(callback)

    async def emit(self, data):
        for callback in self._callbacks:
            if isinstance(data, AudioFile):
                import pdb; pdb.set_trace()
            await callback(data)
        for processor in self._processors:
            await processor.push(data)

    async def push(self, data):
        # logger.debug(f"{self.__class__.__name__} push")
        return await self._push(data)

    async def flush(self):
        # logger.debug(f"{self.__class__.__name__} flush")
        return await self._flush()

    async def _push(self, data):
        raise NotImplementedError

    async def _flush(self):
        pass

    @classmethod
    def as_threaded(cls, *args, **kwargs):
        return ThreadedProcessor(cls(*args, **kwargs), max_workers=1)


class ThreadedProcessor(Processor):
    def __init__(self, processor: Processor, max_workers=1):
        super().__init__()
        self.processor = processor
        self.INPUT_TYPE = processor.INPUT_TYPE
        self.OUTPUT_TYPE = processor.OUTPUT_TYPE
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue = asyncio.Queue()
        self.task = asyncio.get_running_loop().create_task(self.loop())

    async def loop(self):
        while True:
            data = await self.queue.get()
            try:
                if data is None:
                    await self.processor.flush()
                    break
                await self.processor.push(data)
            finally:
                self.queue.task_done()

    async def _push(self, data):
        await self.queue.put(data)

    async def _flush(self):
        await self.queue.put(None)
        await self.queue.join()

    def connect(self, processor: Processor):
        self.processor.connect(processor)

    def disconnect(self, processor: Processor):
        self.processor.disconnect(processor)

    def on(self, callback):
        self.processor.on(callback)


class AudioChunkerProcessor(Processor):
    """
    Assemble audio frames into chunks
    """

    INPUT_TYPE = av.AudioFrame
    OUTPUT_TYPE = list[av.AudioFrame]

    def __init__(self, max_frames=256):
        super().__init__()
        self.frames: list[av.AudioFrame] = []
        self.max_frames = max_frames

    async def _push(self, data: av.AudioFrame):
        self.frames.append(data)
        if len(self.frames) >= self.max_frames:
            await self.flush()

    async def _flush(self):
        frames = self.frames[:]
        self.frames = []
        if frames:
            await self.emit(frames)


class AudioMergeProcessor(Processor):
    """
    Merge audio frame into a single file
    """

    INPUT_TYPE = list[av.AudioFrame]
    OUTPUT_TYPE = AudioFile

    async def _push(self, data: list[av.AudioFrame]):
        if not data:
            return

        # get audio information from first frame
        frame = data[0]
        channels = len(frame.layout.channels)
        sample_rate = frame.sample_rate
        sample_width = frame.format.bytes

        # create audio file
        from time import monotonic_ns
        from uuid import uuid4

        uu = uuid4().hex
        path = Path(f"audio_{monotonic_ns()}_{uu}.wav")
        with wave.open(path.as_posix(), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            for frame in data:
                wf.writeframes(frame.to_ndarray().tobytes())

        # emit audio file
        audiofile = AudioFile(
            path=path,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            timestamp=data[0].pts * data[0].time_base,
        )
        await self.emit(audiofile)


class AudioTranscriptProcessor(Processor):
    """
    Transcript audio file
    """

    INPUT_TYPE = AudioFile
    OUTPUT_TYPE = Transcript

    async def _push(self, data: AudioFile):
        result = await self._transcript(data)
        if result:
            await self.emit(result)

    async def _transcript(self, data: AudioFile):
        raise NotImplementedError


class AudioWhisperTranscriptProcessor(AudioTranscriptProcessor):
    def __init__(self):
        super().__init__()
        self.model = WhisperModel(
            "tiny", device="cpu", compute_type="float32", num_workers=12
        )

    async def _transcript(self, data: AudioFile):
        segments, _ = self.model.transcribe(
            data.path.as_posix(),
            language="en",
            beam_size=5,
            # condition_on_previous_text=True,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        if not segments:
            return

        transcript = Transcript(words=[])
        segments = list(segments)
        ts = data.timestamp

        for segment in segments:
            transcript.text += segment.text
            for word in segment.words:
                transcript.words.append(
                    Word(text=word.word, start=ts + word.start, end=ts + word.end)
                )

        return transcript


class TranscriptLineProcessor(Processor):
    """
    Based on stream of transcript, assemble lines, remove duplicated words
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = Transcript

    def __init__(self, max_text=1000):
        super().__init__()
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

            # emit line
            await self.emit(partial)

            # create new transcript
            partial = Transcript(words=[])

        self.transcript = partial

    async def _flush(self):
        if self.transcript.words:
            await self.emit(self.transcript)


class TitleSummaryProcessor(Processor):
    """
    Detect topic and summary from the transcript
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary

    async def _push(self, data: Transcript):
        param = TitleSummaryInput(transcribed_time=data.timestamp, input_text=data.text)

        try:
            # TODO: abstract LLM implementation and parsing
            response = httpx.post(
                settings.LLM_URL, headers=param.headers, json=param.data
            )
            response.raise_for_status()

            result = ParseLLMResult(param=param, output=response.json())
            summary = TitleSummary(title=result.title, summary=result.description)
            await self.emit(summary)

        except Exception:
            logger.exception("Failed to call llm")
            return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    args = parser.parse_args()

    async def main():
        chunker = AudioChunkerProcessor()

        # merge audio
        merger = AudioMergeProcessor.as_threaded()
        chunker.connect(merger)

        # transcript audio
        transcripter = AudioWhisperTranscriptProcessor()
        merger.connect(transcripter)

        # merge transcript and output lines
        line_processor = TranscriptLineProcessor()
        transcripter.connect(line_processor)

        async def on_transcript(transcript):
            print(f"Transcript: [{transcript.human_timestamp}]: {transcript.text}")

        line_processor.on(on_transcript)

        # # title and summary
        # title_summary = TitleSummaryProcessor.as_threaded()
        # line_processor.connect(title_summary)
        #
        # async def on_summary(summary):
        #     print(f"Summary: title={summary.title} summary={summary.summary}")
        #
        # title_summary.on(on_summary)

        # start processing audio
        container = av.open(args.source)
        for frame in container.decode(audio=0):
            await chunker.push(frame)

        # audio done, flush everything
        await chunker.flush()
        await merger.flush()
        await transcripter.flush()
        await line_processor.flush()
        # await title_summary.flush()

    asyncio.run(main())
