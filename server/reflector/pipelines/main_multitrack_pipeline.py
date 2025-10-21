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
    TranscriptWaveform,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import task_send_webhook_if_needed
from reflector.pipelines.main_live_pipeline import (
    PipelineMainBase,
    broadcast_to_sockets,
    task_cleanup_consent,
    task_pipeline_post_to_zulip,
)
from reflector.processors import (
    AudioFileWriterProcessor,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptTopicDetectorProcessor,
)
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
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
        Uses ffmpeg subprocess approach proven to work with python-raw-tracks-align.

        Returns: (padded_data, storage_url)
        """
        import json
        import math
        import subprocess
        import tempfile

        if not track_data:
            return b"", ""

        transcript = await self.get_transcript()

        # Create temp files for ffmpeg processing
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(track_data)
            input_file_path = input_file.name

        output_file_path = input_file_path.replace(".webm", "_padded.webm")

        try:
            # Get stream metadata using ffprobe
            ffprobe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=start_time",
                "-of",
                "json",
                input_file_path,
            ]

            result = subprocess.run(
                ffprobe_cmd, capture_output=True, text=True, check=True
            )
            metadata = json.loads(result.stdout)

            # Extract start_time from stream metadata
            start_time_seconds = 0.0
            if metadata.get("streams") and len(metadata["streams"]) > 0:
                start_time_str = metadata["streams"][0].get("start_time", "0")
                start_time_seconds = float(start_time_str)

            self.logger.info(
                f"Track {track_idx} stream metadata: start_time={start_time_seconds:.3f}s",
                track_idx=track_idx,
            )

            # If no padding needed, use original
            if start_time_seconds <= 0:
                storage_path = f"file_pipeline/{transcript.id}/tracks/original_track_{track_idx}.webm"
                await storage.put_file(storage_path, track_data)
                url = await storage.get_file_url(storage_path)
                return track_data, url

            # Calculate delay in milliseconds
            delay_ms = math.floor(start_time_seconds * 1000)

            # Run ffmpeg to pad the audio while maintaining WebM/Opus format for Modal compatibility
            # ffmpeg quirk: aresample needs to come before adelay in the filter chain
            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",  # overwrite output
                "-i",
                input_file_path,
                "-af",
                f"aresample=async=1,adelay={delay_ms}:all=true",
                "-c:a",
                "libopus",  # Keep Opus codec for Modal compatibility
                "-b:a",
                "128k",  # Standard bitrate for Opus
                output_file_path,
            ]

            self.logger.info(
                f"Padding track {track_idx} with {delay_ms}ms delay using ffmpeg",
                track_idx=track_idx,
                delay_ms=delay_ms,
                command=" ".join(ffmpeg_cmd),
            )

            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(
                    f"ffmpeg padding failed for track {track_idx}",
                    track_idx=track_idx,
                    stderr=result.stderr,
                    returncode=result.returncode,
                )
                raise Exception(f"ffmpeg padding failed: {result.stderr}")

            # Read the padded output
            with open(output_file_path, "rb") as f:
                padded_data = f.read()

            # Store padded track
            storage_path = (
                f"file_pipeline/{transcript.id}/tracks/padded_track_{track_idx}.webm"
            )
            await storage.put_file(storage_path, padded_data)
            padded_url = await storage.get_file_url(storage_path)

            self.logger.info(
                f"Successfully padded track {track_idx} with {start_time_seconds:.3f}s offset, stored at {storage_path}",
                track_idx=track_idx,
                delay_ms=delay_ms,
                padded_url=padded_url,
                padded_size=len(padded_data),
            )

            return padded_data, padded_url

        finally:
            # Clean up temp files
            import os

            try:
                os.unlink(input_file_path)
            except:
                pass
            try:
                os.unlink(output_file_path)
            except:
                pass

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

    @broadcast_to_sockets
    async def set_status(self, transcript_id: str, status: TranscriptStatus):
        async with self.lock_transaction():
            return await transcripts_controller.set_status(transcript_id, status)

    async def on_waveform(self, data):
        async with self.transaction():
            waveform = TranscriptWaveform(waveform=data)
            transcript = await self.get_transcript()
            return await transcripts_controller.append_event(
                transcript=transcript, event="WAVEFORM", data=waveform
            )

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

        # PAD TRACKS FIRST - this creates full-length tracks with correct timeline
        padded_track_datas: list[bytes] = []
        padded_track_urls: list[str] = []
        for idx, data in enumerate(track_datas):
            if not data:
                padded_track_datas.append(b"")
                padded_track_urls.append("")
                continue

            padded_data, padded_url = await self.pad_track_for_transcription(
                data, idx, storage
            )
            padded_track_datas.append(padded_data)
            padded_track_urls.append(padded_url)
            self.logger.info(f"Padded track {idx} for transcription: {padded_url}")

        # Mixdown PADDED tracks (already aligned with timeline) into transcript.audio_mp3_filename
        try:
            # Ensure data directory exists
            transcript.data_path.mkdir(parents=True, exist_ok=True)

            mp3_writer = AudioFileWriterProcessor(
                path=str(transcript.audio_mp3_filename),
                on_duration=self.on_duration,
            )
            # Use PADDED tracks with NO additional offsets (already aligned by padding)
            await self.mixdown_tracks(
                padded_track_datas, mp3_writer, offsets_seconds=None
            )
            await mp3_writer.flush()

            # Upload the mixed audio to S3 for web playback
            if transcript.audio_mp3_filename.exists():
                mp3_data = transcript.audio_mp3_filename.read_bytes()
                storage_path = f"{transcript.id}/audio.mp3"
                await storage.put_file(storage_path, mp3_data)
                mp3_url = await storage.get_file_url(storage_path)

                # Update transcript to indicate audio is in storage
                await transcripts_controller.update(
                    transcript, {"audio_location": "storage"}
                )

                self.logger.info(
                    f"Uploaded mixed audio to storage",
                    storage_path=storage_path,
                    size=len(mp3_data),
                    url=mp3_url,
                )
            else:
                self.logger.warning("Mixdown file does not exist after processing")
        except Exception as e:
            self.logger.error("Mixdown failed", error=str(e), exc_info=True)

        # Generate waveform from the mixed audio file
        if transcript.audio_mp3_filename.exists():
            try:
                self.logger.info("Generating waveform from mixed audio")
                waveform_processor = AudioWaveformProcessor(
                    audio_path=transcript.audio_mp3_filename,
                    waveform_path=transcript.audio_waveform_filename,
                    on_waveform=self.on_waveform,
                )
                waveform_processor.set_pipeline(self.empty_pipeline)
                await waveform_processor.flush()
                self.logger.info("Waveform generated successfully")
            except Exception as e:
                self.logger.error(
                    "Waveform generation failed", error=str(e), exc_info=True
                )

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

        # Emit TRANSCRIPT event through the shared handler (persists and broadcasts)
        await self.on_transcript(merged_transcript)

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
