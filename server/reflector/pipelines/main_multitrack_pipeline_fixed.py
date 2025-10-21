import asyncio
import io
from fractions import Fraction

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

    async def pad_track_for_transcription(
        self,
        track_data: bytes,
        track_idx: int,
        storage,
    ) -> tuple[bytes, str]:
        """
        Pad a single track with silence based on stream metadata start_time.
        This ensures Whisper timestamps will be relative to recording start.

        Returns: (padded_data, storage_url)
        """
        if not track_data:
            return b"", ""

        transcript = await self.get_transcript()

        # Get stream metadata start_time using PyAV
        container = av.open(io.BytesIO(track_data))
        try:
            audio_stream = container.streams.audio[0]

            # Extract start_time from stream metadata
            if (
                audio_stream.start_time is not None
                and audio_stream.time_base is not None
            ):
                start_time_seconds = float(
                    audio_stream.start_time * audio_stream.time_base
                )
            else:
                start_time_seconds = 0.0

            sample_rate = audio_stream.sample_rate
            codec_name = audio_stream.codec.name
        finally:
            container.close()

        self.logger.info(
            f"Track {track_idx} stream metadata: start_time={start_time_seconds:.3f}s, sample_rate={sample_rate}",
            track_idx=track_idx,
        )

        # If no padding needed, use original
        if start_time_seconds <= 0:
            storage_path = (
                f"file_pipeline/{transcript.id}/tracks/original_track_{track_idx}.webm"
            )
            await storage.put_file(storage_path, track_data)
            url = await storage.get_file_url(storage_path)
            return track_data, url

        # Create PyAV filter graph for padding
        graph = av.filter.Graph()

        # Input buffer
        in_args = (
            f"time_base=1/{sample_rate}:"
            f"sample_rate={sample_rate}:"
            f"sample_fmt=s16:"
            f"channel_layout=stereo"
        )
        input_buffer = graph.add("abuffer", args=in_args, name="in")

        # Add delay filter for padding
        delay_ms = int(start_time_seconds * 1000)
        delay_filter = graph.add(
            "adelay", args=f"delays={delay_ms}|{delay_ms}:all=1", name="delay"
        )

        # Output sink
        sink = graph.add("abuffersink", name="out")

        # Link filters
        input_buffer.link_to(delay_filter)
        delay_filter.link_to(sink)

        graph.configure()

        # Process audio through filter
        output_bytes = io.BytesIO()
        output_container = av.open(output_bytes, "w", format="webm")
        output_stream = output_container.add_stream("libopus", rate=sample_rate)
        output_stream.channels = 2

        # Reopen input for processing
        input_container = av.open(io.BytesIO(track_data))
        resampler = AudioResampler(format="s16", layout="stereo", rate=sample_rate)

        try:
            # Process frames
            for frame in input_container.decode(audio=0):
                # Resample to match filter requirements
                resampled_frames = resampler.resample(frame)
                for resampled_frame in resampled_frames:
                    resampled_frame.pts = frame.pts
                    resampled_frame.time_base = Fraction(1, sample_rate)
                    input_buffer.push(resampled_frame)

                    # Pull from filter and encode
                    while True:
                        try:
                            out_frame = sink.pull()
                            out_frame.pts = out_frame.pts if out_frame.pts else 0
                            out_frame.time_base = Fraction(1, sample_rate)
                            for packet in output_stream.encode(out_frame):
                                output_container.mux(packet)
                        except av.BlockingIOError:
                            break

            # Flush
            input_buffer.push(None)
            while True:
                try:
                    out_frame = sink.pull()
                    for packet in output_stream.encode(out_frame):
                        output_container.mux(packet)
                except (av.BlockingIOError, av.EOFError):
                    break

            # Flush encoder
            for packet in output_stream.encode(None):
                output_container.mux(packet)

        finally:
            input_container.close()
            output_container.close()

        padded_data = output_bytes.getvalue()

        # Store padded track
        storage_path = (
            f"file_pipeline/{transcript.id}/tracks/padded_track_{track_idx}.webm"
        )
        await storage.put_file(storage_path, padded_data)
        padded_url = await storage.get_file_url(storage_path)

        self.logger.info(
            f"Padded track {track_idx} with {start_time_seconds:.3f}s offset, stored at {storage_path}",
            track_idx=track_idx,
            delay_ms=delay_ms,
            padded_url=padded_url,
        )

        return padded_data, padded_url

    async def mixdown_tracks(
        self,
        track_datas: list[bytes],
        writer: AudioFileWriterProcessor,
        offsets_seconds: list[float] | None = None,
    ) -> None:
        """
        Minimal multi-track mixdown using a PyAV filter graph (amix), no resampling.
        """

        # Discover target sample rate from first decodable frame
        target_sample_rate: int | None = None
        for data in track_datas:
            if not data:
                continue
            try:
                container = av.open(io.BytesIO(data))
                try:
                    for frame in container.decode(audio=0):
                        target_sample_rate = frame.sample_rate
                        break
                finally:
                    container.close()
            except Exception:
                continue
            if target_sample_rate:
                break

        if not target_sample_rate:
            self.logger.warning("Mixdown skipped - no decodable audio frames found")
            return

        # Build PyAV filter graph:
        # N abuffer (s32/stereo)
        #   -> optional adelay per input (for alignment)
        #   -> amix (s32)
        #   -> aformat(s16)
        #   -> sink
        graph = av.filter.Graph()
        inputs = []
        valid_track_datas = [d for d in track_datas if d]
        # Align offsets list with the filtered inputs (skip empties)
        input_offsets_seconds = None
        if offsets_seconds is not None:
            input_offsets_seconds = [
                offsets_seconds[i] for i, d in enumerate(track_datas) if d
            ]
        for idx, data in enumerate(valid_track_datas):
            args = (
                f"time_base=1/{target_sample_rate}:"
                f"sample_rate={target_sample_rate}:"
                f"sample_fmt=s32:"
                f"channel_layout=stereo"
            )
            in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
            inputs.append(in_ctx)

        if not inputs:
            self.logger.warning("Mixdown skipped - no valid inputs for graph")
            return

        mixer = graph.add("amix", args=f"inputs={len(inputs)}:normalize=0", name="mix")

        fmt = graph.add(
            "aformat",
            args=(
                f"sample_fmts=s32:channel_layouts=stereo:sample_rates={target_sample_rate}"
            ),
            name="fmt",
        )

        sink = graph.add("abuffersink", name="out")

        # Optional per-input delay before mixing
        delays_ms: list[int] = []
        if input_offsets_seconds is not None:
            base = min(input_offsets_seconds) if input_offsets_seconds else 0.0
            delays_ms = [
                max(0, int(round((o - base) * 1000))) for o in input_offsets_seconds
            ]
        else:
            delays_ms = [0 for _ in inputs]

        for idx, in_ctx in enumerate(inputs):
            delay_ms = delays_ms[idx] if idx < len(delays_ms) else 0
            if delay_ms > 0:
                # adelay requires one value per channel; use same for stereo
                adelay = graph.add(
                    "adelay",
                    args=f"delays={delay_ms}|{delay_ms}:all=1",
                    name=f"delay{idx}",
                )
                in_ctx.link_to(adelay)
                adelay.link_to(mixer, 0, idx)
            else:
                in_ctx.link_to(mixer, 0, idx)
        mixer.link_to(fmt)
        fmt.link_to(sink)
        graph.configure()

        # Open containers for decoding
        containers = []
        for i, d in enumerate(valid_track_datas):
            try:
                c = av.open(io.BytesIO(d))
                containers.append(c)
            except Exception as e:
                self.logger.warning(
                    "Mixdown: failed to open container", input=i, error=str(e)
                )
                containers.append(None)
        # Filter out Nones for decoders
        containers = [c for c in containers if c is not None]
        decoders = [c.decode(audio=0) for c in containers]
        active = [True] * len(decoders)
        # Per-input resamplers to enforce s32/stereo at the same rate (no resample of rate)
        resamplers = [
            AudioResampler(format="s32", layout="stereo", rate=target_sample_rate)
            for _ in decoders
        ]

        try:
            # Round-robin feed frames into graph, pull mixed frames as they become available
            while any(active):
                for i, (dec, is_active) in enumerate(zip(decoders, active)):
                    if not is_active:
                        continue
                    try:
                        frame = next(dec)
                    except StopIteration:
                        active[i] = False
                        continue

                    # Enforce same sample rate; convert format/layout to s16/stereo (no resample)
                    if frame.sample_rate != target_sample_rate:
                        # Skip frames with differing rate
                        continue
                    out_frames = resamplers[i].resample(frame) or []
                    for rf in out_frames:
                        rf.sample_rate = target_sample_rate
                        rf.time_base = Fraction(1, target_sample_rate)
                        inputs[i].push(rf)

                    # Drain available mixed frames
                    while True:
                        try:
                            mixed = sink.pull()
                        except Exception:
                            break
                        mixed.sample_rate = target_sample_rate
                        mixed.time_base = Fraction(1, target_sample_rate)
                        await writer.push(mixed)

            # Signal EOF to inputs and drain remaining
            for in_ctx in inputs:
                in_ctx.push(None)
            while True:
                try:
                    mixed = sink.pull()
                except Exception:
                    break
                mixed.sample_rate = target_sample_rate
                mixed.time_base = Fraction(1, target_sample_rate)
                await writer.push(mixed)
        finally:
            for c in containers:
                c.close()

    async def set_status(self, transcript_id: str, status: TranscriptStatus):
        async with self.lock_transaction():
            return await transcripts_controller.set_status(transcript_id, status)

    async def process(self, bucket_name: str, track_keys: list[str]):
        transcript = await self.get_transcript()

        s3 = boto3.client(
            "s3",
            region_name=settings.RECORDING_STORAGE_AWS_REGION,
            aws_access_key_id=settings.RECORDING_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.RECORDING_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        storage = get_transcripts_storage()

        # Pre-download bytes for all tracks for mixing and transcription
        track_datas: list[bytes] = []
        for key in track_keys:
            try:
                obj = s3.get_object(Bucket=bucket_name, Key=key)
                track_datas.append(obj["Body"].read())
            except Exception as e:
                self.logger.warning(
                    "Skipping track - cannot read S3 object", key=key, error=str(e)
                )
                track_datas.append(b"")

        # REMOVED: Filename offset extraction - not needed anymore!
        # We use stream metadata start_time for padding instead

        # Get stream metadata start_times for mixing (still useful for mixdown)
        stream_start_times: list[float] = []
        for data in track_datas:
            if not data:
                stream_start_times.append(0.0)
                continue

            container = av.open(io.BytesIO(data))
            try:
                audio_stream = container.streams.audio[0]
                if (
                    audio_stream.start_time is not None
                    and audio_stream.time_base is not None
                ):
                    start_time = float(audio_stream.start_time * audio_stream.time_base)
                else:
                    start_time = 0.0
                stream_start_times.append(start_time)
            finally:
                container.close()

        # Mixdown all available tracks into transcript.audio_mp3_filename, using stream metadata offsets
        try:
            mp3_writer = AudioFileWriterProcessor(
                path=str(transcript.audio_mp3_filename)
            )
            await self.mixdown_tracks(track_datas, mp3_writer, stream_start_times)
            await mp3_writer.flush()
        except Exception as e:
            self.logger.error("Mixdown failed", error=str(e))

        # PAD TRACKS BEFORE TRANSCRIPTION - THIS IS THE KEY FIX!
        padded_track_urls: list[str] = []
        for idx, data in enumerate(track_datas):
            if not data:
                padded_track_urls.append("")
                continue

            _, padded_url = await self.pad_track_for_transcription(data, idx, storage)
            padded_track_urls.append(padded_url)
            self.logger.info(f"Padded track {idx} for transcription: {padded_url}")

        # Transcribe PADDED tracks - timestamps will be automatically correct!
        speaker_transcripts: list[TranscriptType] = []
        for idx, padded_url in enumerate(padded_track_urls):
            if not padded_url:
                continue

            try:
                # Transcribe the PADDED track
                t = await self.transcribe_file(padded_url, transcript.source_language)
            except Exception as e:
                self.logger.error(
                    "Transcription via default backend failed, trying local whisper",
                    track_idx=idx,
                    url=padded_url,
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
                            audio_url=padded_url, language=transcript.source_language
                        )
                    )
                    await fallback.flush()
                    if not result:
                        raise Exception("No transcript captured in fallback")
                    t = result
                except Exception as e2:
                    self.logger.error(
                        "Skipping track - transcription failed after fallback",
                        track_idx=idx,
                        url=padded_url,
                        error=str(e2),
                    )
                    continue

            if not t.words:
                continue

            # NO OFFSET ADJUSTMENT NEEDED!
            # Timestamps are already correct because we transcribed padded tracks
            # Just set speaker ID
            for w in t.words:
                w.speaker = idx

            speaker_transcripts.append(t)
            self.logger.info(
                f"Track {idx} transcribed successfully with {len(t.words)} words",
                track_idx=idx,
            )

        if not speaker_transcripts:
            raise Exception("No valid track transcriptions")

        # Merge all words and sort by timestamp
        merged_words = []
        for t in speaker_transcripts:
            merged_words.extend(t.words)
        merged_words.sort(
            key=lambda w: w.start if hasattr(w, "start") and w.start is not None else 0
        )

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
    *, transcript_id: str, bucket_name: str, track_keys: list[str]
):
    pipeline = PipelineMainMultitrack(transcript_id=transcript_id)
    try:
        await pipeline.set_status(transcript_id, "processing")
        await pipeline.process(bucket_name, track_keys)
    except Exception:
        await pipeline.set_status(transcript_id, "error")
        raise

    post_chain = chain(
        task_cleanup_consent.si(transcript_id=transcript_id),
        task_pipeline_post_to_zulip.si(transcript_id=transcript_id),
        task_send_webhook_if_needed.si(transcript_id=transcript_id),
    )
    post_chain.delay()
