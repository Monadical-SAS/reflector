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
import json
from concurrent.futures import ThreadPoolExecutor


@dataclass
class AudioFile:
    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: float = 0.0

    def release(self):
        self.path.unlink()


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

    def __init__(self, callback=None):
        self._processors = []
        self._callbacks = []
        if callback:
            self.on(callback)

    def connect(self, processor: "Processor"):
        """
        Connect this processor output to another processor
        """
        if processor.INPUT_TYPE != self.OUTPUT_TYPE:
            raise ValueError(
                f"Processor {processor} input type {processor.INPUT_TYPE} "
                f"does not match {self.OUTPUT_TYPE}"
            )
        self._processors.append(processor)

    def disconnect(self, processor: "Processor"):
        """
        Disconnect this processor data from another processor
        """
        self._processors.remove(processor)

    def on(self, callback):
        """
        Register a callback to be called when data is emitted
        """
        self._callbacks.append(callback)

    def off(self, callback):
        """
        Unregister a callback to be called when data is emitted
        """
        self._callbacks.remove(callback)

    async def emit(self, data):
        for callback in self._callbacks:
            await callback(data)
        for processor in self._processors:
            await processor.push(data)

    async def push(self, data):
        """
        Push data to this processor. `data` must be of type `INPUT_TYPE`
        The function returns the output of type `OUTPUT_TYPE`
        """
        # logger.debug(f"{self.__class__.__name__} push")
        return await self._push(data)

    async def flush(self):
        """
        Flush data to this processor
        """
        # logger.debug(f"{self.__class__.__name__} flush")
        return await self._flush()

    async def _push(self, data):
        raise NotImplementedError

    async def _flush(self):
        pass

    @classmethod
    def as_threaded(cls, *args, **kwargs):
        """
        Return a single threaded processor where output is guaranteed
        to be in order
        """
        return ThreadedProcessor(cls(*args, **kwargs), max_workers=1)


class ThreadedProcessor(Processor):
    """
    A processor that runs in a separate thread
    """

    def __init__(self, processor: Processor, max_workers=1):
        super().__init__()
        # FIXME: This is a hack to make sure that the processor is single threaded
        # but if it is more than 1, then we need to make sure that the processor
        # is emiting data in order
        assert max_workers == 1
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
        try:
            result = await self._transcript(data)
            if result:
                await self.emit(result)
        finally:
            data.release()

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

        except httpx.ConnectError as e:
            logger.error(f"Failed to call llm: {e}")

        except Exception:
            logger.exception("Failed to call llm")


class Pipeline(Processor):
    """
    A pipeline of processors
    """

    INPUT_TYPE = None
    OUTPUT_TYPE = None

    def __init__(self, *processors):
        super().__init__()
        self.processors = processors

        for i in range(len(processors) - 1):
            processors[i].connect(processors[i + 1])

        self.INPUT_TYPE = processors[0].INPUT_TYPE
        self.OUTPUT_TYPE = processors[-1].OUTPUT_TYPE

    async def _push(self, data):
        await self.processors[0].push(data)

    async def _flush(self):
        for processor in self.processors:
            await processor.flush()


class FinalSummaryProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = Path

    def __init__(self, filename: Path, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename

    async def _push(self, data: TitleSummary):
        with open(self.filename, "a", encoding="utf8") as fd:
            fd.write(json.dumps(data))

    async def _flush(self):
        logger.info(f"Writing to {self.filename}")
        await self.emit(self.filename)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    args = parser.parse_args()

    async def main():
        async def on_transcript(transcript):
            print(f"Transcript: [{transcript.human_timestamp}]: {transcript.text}")

        async def on_summary(summary):
            print(f"Summary: {summary.title} - {summary.summary}")

        async def on_final_summary(path):
            print(f"Final Summary: {path}")

        # transcription output
        result_fn = Path(args.source).with_suffix(".jsonl")

        pipeline = Pipeline(
            AudioChunkerProcessor(),
            AudioMergeProcessor(),
            AudioWhisperTranscriptProcessor().as_threaded(),
            TranscriptLineProcessor(callback=on_transcript),
            TitleSummaryProcessor.as_threaded(callback=on_summary),
            FinalSummaryProcessor.as_threaded(
                filename=result_fn, callback=on_final_summary
            ),
        )

        # start processing audio
        logger.info(f"Opening{args.source}")
        container = av.open(args.source)
        try:
            logger.info("Start pushing audio into the pipeline")
            for frame in container.decode(audio=0):
                await pipeline.push(frame)
        finally:
            logger.info("Flushing the pipeline")
            await pipeline.flush()

        logger.info("All done !")

    asyncio.run(main())
