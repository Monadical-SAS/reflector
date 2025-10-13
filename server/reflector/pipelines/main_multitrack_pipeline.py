import asyncio
import audioop
import io

import av
import boto3
import structlog
from av.audio.resampler import AudioResampler
from celery import chain, shared_task

from reflector.asynctask import asynctask
from reflector.db.transcripts import (
    TranscriptStatus,
    TranscriptText,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import task_send_webhook_if_needed
from reflector.pipelines.main_live_pipeline import (
    PipelineMainBase,
    task_cleanup_consent,
    task_pipeline_post_to_zulip,
)
from reflector.processors import (
    AudioFileWriterProcessor,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptTopicDetectorProcessor,
)
from reflector.processors.file_transcript import FileTranscriptInput
from reflector.processors.file_transcript_auto import FileTranscriptAutoProcessor
from reflector.processors.types import TitleSummary
from reflector.processors.types import (
    Transcript as TranscriptType,
)
from reflector.settings import settings
from reflector.storage import get_transcripts_storage


class EmptyPipeline:
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def get_pref(self, k, d=None):
        return d

    async def emit(self, event):
        pass


class PipelineMainMultitrack(PipelineMainBase):
    """Process multiple participant tracks for a transcript without mixing audio."""

    def __init__(self, transcript_id: str):
        super().__init__(transcript_id=transcript_id)
        self.logger = logger.bind(transcript_id=self.transcript_id)
        self.empty_pipeline = EmptyPipeline(logger=self.logger)

    async def set_status(self, transcript_id: str, status: TranscriptStatus):
        async with self.lock_transaction():
            return await transcripts_controller.set_status(transcript_id, status)

    async def _list_immediate_keys(
        self, s3, bucket_name: str, prefix: str
    ) -> list[str]:
        paginator = s3.get_paginator("list_objects_v2")
        raw_prefix = prefix.rstrip("/")
        prefixes = [raw_prefix, raw_prefix + "/"]

        keys: set[str] = set()
        for pref in prefixes:
            for page in paginator.paginate(Bucket=bucket_name, Prefix=pref):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.startswith(pref):
                        continue
                    if pref.endswith("/"):
                        rel = key[len(pref) :]
                        if not rel or rel.endswith("/") or "/" in rel:
                            continue
                    else:
                        if key != pref:
                            continue
                    keys.add(key)
        result = sorted(keys)
        self.logger.info(
            "S3 list immediate files",
            prefixes=prefixes,
            total_keys=len(result),
            sample=result[:5],
        )
        return result

    async def process(self, bucket_name: str, prefix: str):
        transcript = await self.get_transcript()

        s3 = boto3.client(
            "s3",
            region_name=settings.RECORDING_STORAGE_AWS_REGION,
            aws_access_key_id=settings.RECORDING_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.RECORDING_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        keys = await self._list_immediate_keys(s3, bucket_name, prefix)
        if not keys:
            raise Exception("No audio tracks found under prefix")

        storage = get_transcripts_storage()

        # Pre-download bytes for all tracks for mixing and transcription
        track_datas: list[bytes] = []
        for key in keys:
            try:
                obj = s3.get_object(Bucket=bucket_name, Key=key)
                track_datas.append(obj["Body"].read())
            except Exception as e:
                self.logger.warning(
                    "Skipping track - cannot read S3 object", key=key, error=str(e)
                )
                track_datas.append(b"")

        # Mixdown all available tracks into transcript.audio_mp3_filename at 16kHz mono
        try:
            mp3_writer = AudioFileWriterProcessor(
                path=str(transcript.audio_mp3_filename)
            )

            # Generators for PCM s16 mono 16kHz per track
            def pcm_generator(data: bytes):
                if not data:
                    return
                container = av.open(io.BytesIO(data))
                resampler = AudioResampler(format="s16", layout="mono", rate=16000)
                try:
                    for frame in container.decode(audio=0):
                        rframes = resampler.resample(frame) or []
                        for rf in rframes:
                            # Convert audio plane to raw bytes (PyAV plane supports bytes())
                            yield bytes(rf.planes[0])
                finally:
                    container.close()

            gens = [pcm_generator(d) for d in track_datas if d]
            buffers = [bytearray() for _ in gens]
            active = [True for _ in gens]

            CHUNK_SAMPLES = 16000  # 1 second
            CHUNK_BYTES = CHUNK_SAMPLES * 2  # s16 mono

            while any(active) or any(len(b) > 0 for b in buffers):
                # Fill buffers up to CHUNK_BYTES
                for i, (gen, buf, is_active) in enumerate(zip(gens, buffers, active)):
                    if not is_active:
                        continue
                    while len(buf) < CHUNK_BYTES:
                        try:
                            next_bytes = next(gen)
                            buf.extend(next_bytes)
                        except StopIteration:
                            active[i] = False
                            break

                available_lengths = [len(b) for b in buffers if len(b) > 0]
                if not available_lengths and not any(active):
                    break
                if not available_lengths:
                    continue
                chunk_len = min(min(available_lengths), CHUNK_BYTES)
                chunk_len -= chunk_len % 2
                if chunk_len == 0:
                    continue

                # Mix: scale each track by 1/N then sum
                num_sources = max(1, sum(1 for b in buffers if len(b) >= chunk_len))
                mixed = bytes(chunk_len)
                for buf in buffers:
                    if len(buf) >= chunk_len:
                        part = bytes(buf[:chunk_len])
                        del buf[:chunk_len]
                    else:
                        if len(buf) == 0:
                            continue
                        part = bytes(buf)
                        del buf[:]
                        part = part + bytes(chunk_len - len(part))
                    scaled = audioop.mul(part, 2, 1.0 / num_sources)
                    mixed = audioop.add(mixed, scaled, 2)

                # Encode mixed frame to MP3
                num_samples = chunk_len // 2
                frame = av.AudioFrame(format="s16", layout="mono", samples=num_samples)
                frame.sample_rate = 16000
                frame.planes[0].update(mixed)
                await mp3_writer.push(frame)

            await mp3_writer.flush()
        except Exception as e:
            self.logger.warning("Mixdown failed", error=str(e))

        speaker_transcripts: list[TranscriptType] = []
        for idx, key in enumerate(keys):
            ext = ".mp4"

            try:
                obj = s3.get_object(Bucket=bucket_name, Key=key)
                data = obj["Body"].read()
            except Exception as e:
                self.logger.warning(
                    "Skipping track - cannot read S3 object", key=key, error=str(e)
                )
                continue

            storage_path = f"file_pipeline/{transcript.id}/tracks/track_{idx}{ext}"
            try:
                await storage.put_file(storage_path, data)
                audio_url = await storage.get_file_url(storage_path)
            except Exception as e:
                self.logger.warning(
                    "Skipping track - cannot upload to storage", key=key, error=str(e)
                )
                continue

            try:
                t = await self.transcribe_file(audio_url, transcript.source_language)
            except Exception as e:
                self.logger.warning(
                    "Transcription via default backend failed, trying local whisper",
                    key=key,
                    url=audio_url,
                    error=str(e),
                )
                try:
                    fallback = FileTranscriptAutoProcessor(name="whisper")
                    result = None

                    async def capture_result(r):
                        nonlocal result
                        result = r

                    fallback.on(capture_result)
                    await fallback.push(
                        FileTranscriptInput(
                            audio_url=audio_url, language=transcript.source_language
                        )
                    )
                    await fallback.flush()
                    if not result:
                        raise Exception("No transcript captured in fallback")
                    t = result
                except Exception as e2:
                    self.logger.warning(
                        "Skipping track - transcription failed after fallback",
                        key=key,
                        url=audio_url,
                        error=str(e2),
                    )
                    continue

            if not t.words:
                continue
            for w in t.words:
                w.speaker = idx
            speaker_transcripts.append(t)

        if not speaker_transcripts:
            raise Exception("No valid track transcriptions")

        merged_words = []
        for t in speaker_transcripts:
            merged_words.extend(t.words)
        merged_words.sort(key=lambda w: w.start)

        merged_transcript = TranscriptType(words=merged_words, translation=None)

        await transcripts_controller.append_event(
            transcript,
            event="TRANSCRIPT",
            data=TranscriptText(
                text=merged_transcript.text, translation=merged_transcript.translation
            ),
        )

        topics = await self.detect_topics(merged_transcript, transcript.target_language)
        await asyncio.gather(
            self.generate_title(topics),
            self.generate_summaries(topics),
            return_exceptions=False,
        )

        await self.set_status(transcript.id, "ended")

    async def transcribe_file(self, audio_url: str, language: str) -> TranscriptType:
        processor = FileTranscriptAutoProcessor()
        input_data = FileTranscriptInput(audio_url=audio_url, language=language)

        result: TranscriptType | None = None

        async def capture_result(transcript):
            nonlocal result
            result = transcript

        processor.on(capture_result)
        await processor.push(input_data)
        await processor.flush()

        if not result:
            raise ValueError("No transcript captured")

        return result

    async def detect_topics(
        self, transcript: TranscriptType, target_language: str
    ) -> list[TitleSummary]:
        chunk_size = 300
        topics: list[TitleSummary] = []

        async def on_topic(topic: TitleSummary):
            topics.append(topic)
            return await self.on_topic(topic)

        topic_detector = TranscriptTopicDetectorProcessor(callback=on_topic)
        topic_detector.set_pipeline(self.empty_pipeline)

        for i in range(0, len(transcript.words), chunk_size):
            chunk_words = transcript.words[i : i + chunk_size]
            if not chunk_words:
                continue

            chunk_transcript = TranscriptType(
                words=chunk_words, translation=transcript.translation
            )
            await topic_detector.push(chunk_transcript)

        await topic_detector.flush()
        return topics

    async def generate_title(self, topics: list[TitleSummary]):
        if not topics:
            self.logger.warning("No topics for title generation")
            return

        processor = TranscriptFinalTitleProcessor(callback=self.on_title)
        processor.set_pipeline(self.empty_pipeline)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()

    async def generate_summaries(self, topics: list[TitleSummary]):
        if not topics:
            self.logger.warning("No topics for summary generation")
            return

        transcript = await self.get_transcript()
        processor = TranscriptFinalSummaryProcessor(
            transcript=transcript,
            callback=self.on_long_summary,
            on_short_summary=self.on_short_summary,
        )
        processor.set_pipeline(self.empty_pipeline)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()


@shared_task
@asynctask
async def task_pipeline_multitrack_process(
    *, transcript_id: str, bucket_name: str, prefix: str
):
    pipeline = PipelineMainMultitrack(transcript_id=transcript_id)
    try:
        await pipeline.set_status(transcript_id, "processing")
        await pipeline.process(bucket_name, prefix)
    except Exception:
        await pipeline.set_status(transcript_id, "error")
        raise

    post_chain = chain(
        task_cleanup_consent.si(transcript_id=transcript_id),
        task_pipeline_post_to_zulip.si(transcript_id=transcript_id),
        task_send_webhook_if_needed.si(transcript_id=transcript_id),
    )
    post_chain.delay()
