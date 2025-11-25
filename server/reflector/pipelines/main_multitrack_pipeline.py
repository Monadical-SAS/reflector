import asyncio
import math
import tempfile
from fractions import Fraction
from pathlib import Path

import av
from av.audio.resampler import AudioResampler
from celery import chain, shared_task

from reflector.asynctask import asynctask
from reflector.db.transcripts import (
    TranscriptStatus,
    TranscriptWaveform,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines import topic_processing
from reflector.pipelines.main_file_pipeline import task_send_webhook_if_needed
from reflector.pipelines.main_live_pipeline import (
    PipelineMainBase,
    broadcast_to_sockets,
    task_cleanup_consent,
    task_pipeline_post_to_zulip,
)
from reflector.pipelines.transcription_helpers import transcribe_file_with_processor
from reflector.processors import AudioFileWriterProcessor
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.processors.types import TitleSummary
from reflector.processors.types import Transcript as TranscriptType
from reflector.storage import Storage, get_transcripts_storage
from reflector.utils.string import NonEmptyString

# Audio encoding constants
OPUS_STANDARD_SAMPLE_RATE = 48000
OPUS_DEFAULT_BIT_RATE = 128000

# Storage operation constants
PRESIGNED_URL_EXPIRATION_SECONDS = 7200  # 2 hours


class PipelineMainMultitrack(PipelineMainBase):
    def __init__(self, transcript_id: str):
        super().__init__(transcript_id=transcript_id)
        self.logger = logger.bind(transcript_id=self.transcript_id)
        self.empty_pipeline = topic_processing.EmptyPipeline(logger=self.logger)

    async def pad_track_for_transcription(
        self,
        track_url: NonEmptyString,
        track_idx: int,
        storage: Storage,
    ) -> NonEmptyString:
        """
        Pad a single track with silence based on stream metadata start_time.
        Downloads from S3 presigned URL, processes via PyAV using tempfile, uploads to S3.
        Returns presigned URL of padded track (or original URL if no padding needed).

        Memory usage:
        - Pattern: fixed_overhead(2-5MB) for PyAV codec/filters
        - PyAV streams input efficiently (no full download, verified)
        - Output written to tempfile (disk-based, not memory)
        - Upload streams from file handle (boto3 chunks, typically 5-10MB)

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

        Padding coincidentally involves re-encoding. It's important when we work with Daily.co + Whisper.
        This is because Daily.co returns recordings with skipped frames e.g. when microphone muted.
        Daily.co doesn't understand those frames and ignores them, causing timestamp issues in transcription.
        Re-encoding restores those frames. We do padding and re-encoding together just because it's convenient and more performant:
        we need padded values for mix mp3 anyways
        """

        transcript = await self.get_transcript()

        try:
            # PyAV streams input from S3 URL efficiently (2-5MB fixed overhead for codec/filters)
            with av.open(track_url) as in_container:
                start_time_seconds = self._extract_stream_start_time_from_container(
                    in_container, track_idx
                )

                if start_time_seconds <= 0:
                    self.logger.info(
                        f"Track {track_idx} requires no padding (start_time={start_time_seconds}s)",
                        track_idx=track_idx,
                    )
                    return track_url

                # Use tempfile instead of BytesIO for better memory efficiency
                # Reduces peak memory usage during encoding/upload
                with tempfile.NamedTemporaryFile(
                    suffix=".webm", delete=False
                ) as temp_file:
                    temp_path = temp_file.name

                try:
                    self._apply_audio_padding_to_file(
                        in_container, temp_path, start_time_seconds, track_idx
                    )

                    storage_path = (
                        f"file_pipeline/{transcript.id}/tracks/padded_{track_idx}.webm"
                    )

                    # Upload using file handle for streaming
                    with open(temp_path, "rb") as padded_file:
                        await storage.put_file(storage_path, padded_file)
                finally:
                    # Clean up temp file
                    Path(temp_path).unlink(missing_ok=True)

                padded_url = await storage.get_file_url(
                    storage_path,
                    operation="get_object",
                    expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
                )

                self.logger.info(
                    f"Successfully padded track {track_idx}",
                    track_idx=track_idx,
                    start_time_seconds=start_time_seconds,
                    padded_url=padded_url,
                )

                return padded_url

        except Exception as e:
            self.logger.error(
                f"Failed to process track {track_idx}",
                track_idx=track_idx,
                url=track_url,
                error=str(e),
                exc_info=True,
            )
            raise Exception(
                f"Track {track_idx} padding failed - transcript would have incorrect timestamps"
            ) from e

    def _extract_stream_start_time_from_container(
        self, container, track_idx: int
    ) -> float:
        """
        Extract meeting-relative start time from WebM stream metadata.
        Uses PyAV to read stream.start_time from WebM container.
        More accurate than filename timestamps by ~209ms due to network/encoding delays.
        """
        start_time_seconds = 0.0
        try:
            audio_streams = [s for s in container.streams if s.type == "audio"]
            stream = audio_streams[0] if audio_streams else container.streams[0]

            # 1) Try stream-level start_time (most reliable for Daily.co tracks)
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

    def _apply_audio_padding_to_file(
        self,
        in_container,
        output_path: str,
        start_time_seconds: float,
        track_idx: int,
    ) -> None:
        """Apply silence padding to audio track using PyAV filter graph, writing to file"""
        delay_ms = math.floor(start_time_seconds * 1000)

        self.logger.info(
            f"Padding track {track_idx} with {delay_ms}ms delay using PyAV",
            track_idx=track_idx,
            delay_ms=delay_ms,
        )

        try:
            with av.open(output_path, "w", format="webm") as out_container:
                in_stream = next(
                    (s for s in in_container.streams if s.type == "audio"), None
                )
                if in_stream is None:
                    raise Exception("No audio stream in input")

                out_stream = out_container.add_stream(
                    "libopus", rate=OPUS_STANDARD_SAMPLE_RATE
                )
                out_stream.bit_rate = OPUS_DEFAULT_BIT_RATE
                graph = av.filter.Graph()

                abuf_args = (
                    f"time_base=1/{OPUS_STANDARD_SAMPLE_RATE}:"
                    f"sample_rate={OPUS_STANDARD_SAMPLE_RATE}:"
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

                resampler = AudioResampler(
                    format="s16", layout="stereo", rate=OPUS_STANDARD_SAMPLE_RATE
                )
                # Decode -> resample -> push through graph -> encode Opus
                for frame in in_container.decode(in_stream):
                    out_frames = resampler.resample(frame) or []
                    for rframe in out_frames:
                        rframe.sample_rate = OPUS_STANDARD_SAMPLE_RATE
                        rframe.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
                        src.push(rframe)

                        while True:
                            try:
                                f_out = sink.pull()
                            except Exception:
                                break
                            f_out.sample_rate = OPUS_STANDARD_SAMPLE_RATE
                            f_out.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
                            for packet in out_stream.encode(f_out):
                                out_container.mux(packet)

                src.push(None)
                while True:
                    try:
                        f_out = sink.pull()
                    except Exception:
                        break
                    f_out.sample_rate = OPUS_STANDARD_SAMPLE_RATE
                    f_out.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
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
        track_urls: list[str],
        writer: AudioFileWriterProcessor,
        offsets_seconds: list[float] | None = None,
    ) -> None:
        """Multi-track mixdown using PyAV filter graph (amix), reading from S3 presigned URLs"""

        target_sample_rate: int | None = None
        for url in track_urls:
            if not url:
                continue
            container = None
            try:
                container = av.open(url)
                for frame in container.decode(audio=0):
                    target_sample_rate = frame.sample_rate
                    break
            except Exception:
                continue
            finally:
                if container is not None:
                    container.close()
            if target_sample_rate:
                break

        if not target_sample_rate:
            self.logger.error("Mixdown failed - no decodable audio frames found")
            raise Exception("Mixdown failed: No decodable audio frames in any track")
        # Build PyAV filter graph:
        # N abuffer (s32/stereo)
        #   -> optional adelay per input (for alignment)
        #   -> amix (s32)
        #   -> aformat(s16)
        #   -> sink
        graph = av.filter.Graph()
        inputs = []
        valid_track_urls = [url for url in track_urls if url]
        input_offsets_seconds = None
        if offsets_seconds is not None:
            input_offsets_seconds = [
                offsets_seconds[i] for i, url in enumerate(track_urls) if url
            ]
        for idx, url in enumerate(valid_track_urls):
            args = (
                f"time_base=1/{target_sample_rate}:"
                f"sample_rate={target_sample_rate}:"
                f"sample_fmt=s32:"
                f"channel_layout=stereo"
            )
            in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
            inputs.append(in_ctx)

        if not inputs:
            self.logger.error("Mixdown failed - no valid inputs for graph")
            raise Exception("Mixdown failed: No valid inputs for filter graph")

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

        containers = []
        try:
            # Open all containers with cleanup guaranteed
            for i, url in enumerate(valid_track_urls):
                try:
                    c = av.open(url)
                    containers.append(c)
                except Exception as e:
                    self.logger.warning(
                        "Mixdown: failed to open container from URL",
                        input=i,
                        url=url,
                        error=str(e),
                    )

            if not containers:
                self.logger.error("Mixdown failed - no valid containers opened")
                raise Exception("Mixdown failed: Could not open any track containers")

            decoders = [c.decode(audio=0) for c in containers]
            active = [True] * len(decoders)
            resamplers = [
                AudioResampler(format="s32", layout="stereo", rate=target_sample_rate)
                for _ in decoders
            ]

            while any(active):
                for i, (dec, is_active) in enumerate(zip(decoders, active)):
                    if not is_active:
                        continue
                    try:
                        frame = next(dec)
                    except StopIteration:
                        active[i] = False
                        continue

                    if frame.sample_rate != target_sample_rate:
                        continue
                    out_frames = resamplers[i].resample(frame) or []
                    for rf in out_frames:
                        rf.sample_rate = target_sample_rate
                        rf.time_base = Fraction(1, target_sample_rate)
                        inputs[i].push(rf)

                    while True:
                        try:
                            mixed = sink.pull()
                        except Exception:
                            break
                        mixed.sample_rate = target_sample_rate
                        mixed.time_base = Fraction(1, target_sample_rate)
                        await writer.push(mixed)

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
            # Cleanup all containers, even if processing failed
            for c in containers:
                if c is not None:
                    try:
                        c.close()
                    except Exception:
                        pass  # Best effort cleanup

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
        async with self.transaction():
            await transcripts_controller.update(
                transcript,
                {
                    "events": [],
                    "topics": [],
                },
            )

        source_storage = get_transcripts_storage()
        transcript_storage = source_storage

        track_urls: list[str] = []
        for key in track_keys:
            url = await source_storage.get_file_url(
                key,
                operation="get_object",
                expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
                bucket=bucket_name,
            )
            track_urls.append(url)
            self.logger.info(
                f"Generated presigned URL for track from {bucket_name}",
                key=key,
            )

        created_padded_files = set()
        padded_track_urls: list[str] = []
        for idx, url in enumerate(track_urls):
            padded_url = await self.pad_track_for_transcription(
                url, idx, transcript_storage
            )
            padded_track_urls.append(padded_url)
            if padded_url != url:
                storage_path = f"file_pipeline/{transcript.id}/tracks/padded_{idx}.webm"
                created_padded_files.add(storage_path)
            self.logger.info(f"Track {idx} processed, padded URL: {padded_url}")

        transcript.data_path.mkdir(parents=True, exist_ok=True)

        mp3_writer = AudioFileWriterProcessor(
            path=str(transcript.audio_mp3_filename),
            on_duration=self.on_duration,
        )
        await self.mixdown_tracks(padded_track_urls, mp3_writer, offsets_seconds=None)
        await mp3_writer.flush()

        if not transcript.audio_mp3_filename.exists():
            raise Exception(
                "Mixdown failed - no MP3 file generated. Cannot proceed without playable audio."
            )

        storage_path = f"{transcript.id}/audio.mp3"
        # Use file handle streaming to avoid loading entire MP3 into memory
        mp3_size = transcript.audio_mp3_filename.stat().st_size
        with open(transcript.audio_mp3_filename, "rb") as mp3_file:
            await transcript_storage.put_file(storage_path, mp3_file)
        mp3_url = await transcript_storage.get_file_url(storage_path)

        await transcripts_controller.update(transcript, {"audio_location": "storage"})

        self.logger.info(
            f"Uploaded mixed audio to storage",
            storage_path=storage_path,
            size=mp3_size,
            url=mp3_url,
        )

        self.logger.info("Generating waveform from mixed audio")
        waveform_processor = AudioWaveformProcessor(
            audio_path=transcript.audio_mp3_filename,
            waveform_path=transcript.audio_waveform_filename,
            on_waveform=self.on_waveform,
        )
        waveform_processor.set_pipeline(self.empty_pipeline)
        await waveform_processor.flush()
        self.logger.info("Waveform generated successfully")

        speaker_transcripts: list[TranscriptType] = []
        for idx, padded_url in enumerate(padded_track_urls):
            if not padded_url:
                continue

            t = await self.transcribe_file(padded_url, transcript.source_language)

            if not t.words:
                self.logger.debug(f"no words in track {idx}")
                # not skipping, it may be silence or indistinguishable mumbling

            for w in t.words:
                w.speaker = idx

            speaker_transcripts.append(t)
            self.logger.info(
                f"Track {idx} transcribed successfully with {len(t.words)} words",
                track_idx=idx,
            )

        valid_track_count = len([url for url in padded_track_urls if url])
        if valid_track_count > 0 and len(speaker_transcripts) != valid_track_count:
            raise Exception(
                f"Only {len(speaker_transcripts)}/{valid_track_count} tracks transcribed successfully. "
                f"All tracks must succeed to avoid incomplete transcripts."
            )

        if not speaker_transcripts:
            raise Exception("No valid track transcriptions")

        self.logger.info(f"Cleaning up {len(created_padded_files)} temporary S3 files")
        cleanup_tasks = []
        for storage_path in created_padded_files:
            cleanup_tasks.append(transcript_storage.delete_file(storage_path))

        if cleanup_tasks:
            cleanup_results = await asyncio.gather(
                *cleanup_tasks, return_exceptions=True
            )
            for storage_path, result in zip(created_padded_files, cleanup_results):
                if isinstance(result, Exception):
                    self.logger.warning(
                        "Failed to cleanup temporary padded track",
                        storage_path=storage_path,
                        error=str(result),
                    )

        merged_words = []
        for t in speaker_transcripts:
            merged_words.extend(t.words)
        merged_words.sort(
            key=lambda w: w.start if hasattr(w, "start") and w.start is not None else 0
        )

        merged_transcript = TranscriptType(words=merged_words, translation=None)

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
        return await topic_processing.detect_topics(
            transcript,
            target_language,
            on_topic_callback=self.on_topic,
            empty_pipeline=self.empty_pipeline,
        )

    async def generate_title(self, topics: list[TitleSummary]):
        return await topic_processing.generate_title(
            topics,
            on_title_callback=self.on_title,
            empty_pipeline=self.empty_pipeline,
            logger=self.logger,
        )

    async def generate_summaries(self, topics: list[TitleSummary]):
        transcript = await self.get_transcript()
        return await topic_processing.generate_summaries(
            topics,
            transcript,
            on_long_summary_callback=self.on_long_summary,
            on_short_summary_callback=self.on_short_summary,
            empty_pipeline=self.empty_pipeline,
            logger=self.logger,
        )


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
