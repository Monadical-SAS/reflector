import asyncio
import io
import math
import os
import tempfile
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
from reflector.pipelines.transcription_helpers import transcribe_file_with_processor
from reflector.processors import (
    AudioFileWriterProcessor,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptTopicDetectorProcessor,
)
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.processors.types import TitleSummary
from reflector.processors.types import (
    Transcript as TranscriptType,
)
from reflector.settings import settings
from reflector.storage import get_transcripts_storage
from reflector.storage.base import Storage


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
        storage: Storage,
    ) -> tuple[bytes, str]:
        """
        Pad a single track with silence based on stream metadata start_time.
        This ensures Whisper timestamps will be relative to recording start.
        Implemented with PyAV filter graph (aresample -> adelay) and encoded to WebM/Opus.

        Stores padded track temporarily to S3 to generate URL for Modal API transcription.
        These temporary files should be cleaned up after transcription completes.

        Daily.co raw-tracks timing - Two approaches:

            CURRENT APPROACH (PyAV metadata):
            The WebM stream.start_time field encodes MEETING-RELATIVE timing:
            - t=0: When Daily.co recording started (first participant joined)
            - start_time=8.13s: This participant's track began 8.13s after recording started
            - Purpose: Enables track alignment without external manifest files

            This is NOT:
            - Stream-internal offset (first packet timestamp relative to stream start)
            - Absolute/wall-clock time
            - Recording duration

            ALTERNATIVE APPROACH (filename parsing):
            Daily.co filenames contain Unix timestamps (milliseconds):
            Format: {recording_start_ts}-{participant_id}-cam-audio-{track_start_ts}.webm
            Example: 1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922.webm

            Can calculate offset: (track_start_ts - recording_start_ts) / 1000
            - Track 0: (1760988935922 - 1760988935484) / 1000 = 0.438s
            - Track 1: (1760988943823 - 1760988935484) / 1000 = 8.339s

            TIME DIFFERENCE: PyAV metadata vs filename timestamps differ by ~209ms:
            - Track 0: filename=438ms, metadata=229ms (diff: 209ms)
            - Track 1: filename=8339ms, metadata=8130ms (diff: 209ms)

            Consistent delta suggests network/encoding delay. PyAV metadata is ground truth
            (represents when audio stream actually started vs when file upload initiated).

            Example with 2 participants:
                Track A: start_time=0.2s → Joined 200ms after recording began
                Track B: start_time=8.1s → Joined 8.1 seconds later

                After padding:
                    Track A: [0.2s silence] + [speech...]
                    Track B: [8.1s silence] + [speech...]

                Whisper transcription timestamps are now synchronized:
                    Track A word at 5.0s → happened at meeting t=5.0s
                    Track B word at 10.0s → happened at meeting t=10.0s

                Merging just sorts by timestamp - no offset calculation needed.

        Returns: (padded_data, temp_url_for_transcription)
        """

        if not track_data:
            return b"", ""

        transcript = await self.get_transcript()

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(track_data)
            input_file_path = input_file.name

        output_file_path = input_file_path.replace(".webm", "_padded.webm")

        try:
            start_time_seconds = self._extract_stream_start_time(
                input_file_path, track_idx
            )

            # Determine data to transcribe (original or padded)
            if start_time_seconds <= 0:
                self.logger.info(
                    f"Track {track_idx} requires no padding (start_time={start_time_seconds}s)",
                    track_idx=track_idx,
                )
                data_for_transcription = track_data
            else:
                self._apply_audio_padding(
                    input_file_path, output_file_path, start_time_seconds, track_idx
                )

                with open(output_file_path, "rb") as f:
                    data_for_transcription = f.read()

                self.logger.info(
                    f"Successfully padded track {track_idx}",
                    track_idx=track_idx,
                    start_time_seconds=start_time_seconds,
                    padded_size=len(data_for_transcription),
                )

            # Store temporarily for Modal API (requires URL)
            storage_path = (
                f"file_pipeline/{transcript.id}/tracks/temp_track_{track_idx}.webm"
            )
            await storage.put_file(storage_path, data_for_transcription)
            temp_url = await storage.get_file_url(storage_path)

            return data_for_transcription, temp_url

        finally:
            try:
                os.unlink(input_file_path)
            except OSError as e:
                self.logger.warning(
                    "Failed to cleanup temp input file",
                    path=input_file_path,
                    error=str(e),
                )
            try:
                os.unlink(output_file_path)
            except OSError as e:
                self.logger.warning(
                    "Failed to cleanup temp output file",
                    path=output_file_path,
                    error=str(e),
                )

    def _extract_stream_start_time(self, input_file_path: str, track_idx: int) -> float:
        """
        Extract meeting-relative start time from WebM stream metadata.

        Uses PyAV to read stream.start_time from WebM container (not filename parsing).
        This is more accurate than filename timestamps by ~209ms due to network/encoding delays.

        """
        start_time_seconds = 0.0
        try:
            with av.open(input_file_path) as container:
                # Prefer the first audio stream if present
                audio_streams = [s for s in container.streams if s.type == "audio"]
                stream = audio_streams[0] if audio_streams else container.streams[0]

                # 1) Use stream.start_time in stream.time_base units
                if stream.start_time is not None and stream.time_base is not None:
                    start_time_seconds = float(stream.start_time * stream.time_base)

                # 2) Fallback to container-level start_time (in av.time_base units)
                if (start_time_seconds <= 0) and (container.start_time is not None):
                    start_time_seconds = float(container.start_time * av.time_base)

                # 3) Fallback to first packet DTS in stream.time_base
                if start_time_seconds <= 0:
                    for packet in container.demux(stream):
                        if packet.dts is not None:
                            start_time_seconds = float(packet.dts * stream.time_base)
                            break
        except Exception as e:
            self.logger.warning(
                "PyAV metadata read failed; assuming 0 start_time",
                track_idx=track_idx,
                error=str(e),
            )
            start_time_seconds = 0.0

        self.logger.info(
            f"Track {track_idx} stream metadata: start_time={start_time_seconds:.3f}s",
            track_idx=track_idx,
        )
        return start_time_seconds

    def _apply_audio_padding(
        self,
        input_file_path: str,
        output_file_path: str,
        start_time_seconds: float,
        track_idx: int,
    ) -> None:
        """
        Apply silence padding to audio track using PyAV filter graph.
        Writes padded audio to output_file_path.

        Raises: Exception if padding fails
        """
        delay_ms = math.floor(start_time_seconds * 1000)

        self.logger.info(
            f"Padding track {track_idx} with {delay_ms}ms delay using PyAV",
            track_idx=track_idx,
            delay_ms=delay_ms,
        )

        try:
            # Open input and prepare output container
            with (
                av.open(input_file_path) as in_container,
                av.open(output_file_path, "w") as out_container,
            ):
                # Pick first audio stream
                in_stream = next(
                    (s for s in in_container.streams if s.type == "audio"), None
                )
                if in_stream is None:
                    raise Exception("No audio stream in input file")

                # Use standard Opus sample rate
                out_sample_rate = 48000

                # Create Opus audio stream
                out_stream = out_container.add_stream("libopus", rate=out_sample_rate)
                # 128 kbps target (Opus), matching previous configuration
                out_stream.bit_rate = 128000

                # Build filter graph: abuffer -> aresample (async=1) -> adelay -> sink
                graph = av.filter.Graph()

                # We'll feed s16/stereo/48k frames to abuffer
                abuf_args = (
                    f"time_base=1/{out_sample_rate}:"
                    f"sample_rate={out_sample_rate}:"
                    f"sample_fmt=s16:"
                    f"channel_layout=stereo"
                )
                src = graph.add("abuffer", args=abuf_args, name="src")
                aresample_f = graph.add("aresample", args="async=1", name="ares")

                # adelay requires one delay value per channel separated by '|'
                delays_arg = f"{delay_ms}|{delay_ms}"
                adelay_f = graph.add(
                    "adelay", args=f"delays={delays_arg}:all=1", name="delay"
                )
                sink = graph.add("abuffersink", name="sink")

                src.link_to(aresample_f)
                aresample_f.link_to(adelay_f)
                adelay_f.link_to(sink)
                graph.configure()

                # Resample incoming frames to s16/stereo/48k for graph and encoder
                resampler = AudioResampler(
                    format="s16", layout="stereo", rate=out_sample_rate
                )

                # Decode -> resample -> push through graph -> encode Opus
                for frame in in_container.decode(in_stream):
                    out_frames = resampler.resample(frame) or []
                    for rframe in out_frames:
                        rframe.sample_rate = out_sample_rate
                        rframe.time_base = Fraction(1, out_sample_rate)
                        src.push(rframe)

                        # Drain available frames from sink and encode
                        while True:
                            try:
                                f_out = sink.pull()
                            except Exception:
                                break
                            f_out.sample_rate = out_sample_rate
                            f_out.time_base = Fraction(1, out_sample_rate)
                            for packet in out_stream.encode(f_out):
                                out_container.mux(packet)

                # Flush filter graph and encoder
                src.push(None)
                while True:
                    try:
                        f_out = sink.pull()
                    except Exception:
                        break
                    f_out.sample_rate = out_sample_rate
                    f_out.time_base = Fraction(1, out_sample_rate)
                    for packet in out_stream.encode(f_out):
                        out_container.mux(packet)

                for packet in out_stream.encode(None):
                    out_container.mux(packet)
        except Exception as e:
            self.logger.error(
                "PyAV padding failed for track",
                track_idx=track_idx,
                delay_ms=delay_ms,
                error=str(e),
                exc_info=True,
            )
            raise

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

        # Clear transcript as we're going to regenerate everything
        async with self.transaction():
            await transcripts_controller.update(
                transcript,
                {
                    "events": [],
                    "topics": [],
                },
            )

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
                    "Skipping track - cannot read S3 object",
                    key=key,
                    error=str(e),
                    exc_info=True,
                )
                track_datas.append(b"")

        # Early validation: fail fast if any downloads failed
        valid_track_count = sum(1 for d in track_datas if d)
        if valid_track_count < len(track_keys):
            raise Exception(
                f"Failed to download {len(track_keys) - valid_track_count}/{len(track_keys)} tracks from S3 bucket {bucket_name}"
            )

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

        try:
            transcript.data_path.mkdir(parents=True, exist_ok=True)

            mp3_writer = AudioFileWriterProcessor(
                path=str(transcript.audio_mp3_filename),
                on_duration=self.on_duration,
            )
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

        speaker_transcripts: list[TranscriptType] = []
        for idx, padded_url in enumerate(padded_track_urls):
            if not padded_url:
                continue

            try:
                t = await self.transcribe_file(padded_url, transcript.source_language)
            except Exception as e:
                self.logger.error(
                    "Transcription via default backend failed, trying local whisper",
                    track_idx=idx,
                    url=padded_url,
                    error=str(e),
                )
                try:
                    t = await transcribe_file_with_processor(
                        padded_url, transcript.source_language, processor_name="whisper"
                    )
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

            for w in t.words:
                w.speaker = idx

            speaker_transcripts.append(t)
            self.logger.info(
                f"Track {idx} transcribed successfully with {len(t.words)} words",
                track_idx=idx,
            )

        if not speaker_transcripts:
            raise Exception("No valid track transcriptions")

        self.logger.info(f"Cleaning up {len(padded_track_urls)} temporary S3 files")
        cleanup_tasks = []
        for idx, url in enumerate(padded_track_urls):
            if url:
                storage_path = (
                    f"file_pipeline/{transcript.id}/tracks/temp_track_{idx}.webm"
                )
                cleanup_tasks.append(storage.delete_file(storage_path))

        if cleanup_tasks:
            cleanup_results = await asyncio.gather(
                *cleanup_tasks, return_exceptions=True
            )
            for idx, result in enumerate(cleanup_results):
                if isinstance(result, Exception):
                    self.logger.warning(
                        f"Failed to cleanup temp track file {idx}",
                        error=str(result),
                    )

        # Merge all words and sort by timestamp (monotonic invariant before topic detection)
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
        return await transcribe_file_with_processor(audio_url, language)

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
