import asyncio
import tempfile
from pathlib import Path

import av
from celery import chain, shared_task

from reflector.asynctask import asynctask
from reflector.dailyco_api import MeetingParticipantsResponse
from reflector.db.transcripts import (
    Transcript,
    TranscriptParticipant,
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
from reflector.utils.audio_constants import PRESIGNED_URL_EXPIRATION_SECONDS
from reflector.utils.audio_mixdown import (
    detect_sample_rate_from_tracks,
    mixdown_tracks_pyav,
)
from reflector.utils.audio_padding import (
    apply_audio_padding_to_file,
    extract_stream_start_time_from_container,
)
from reflector.utils.daily import (
    filter_cam_audio_tracks,
    parse_daily_recording_filename,
)
from reflector.utils.string import NonEmptyString
from reflector.video_platforms.factory import create_platform_client


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

            TIME DIFFERENCE: PyAV metadata vs filename timestamps differ by ~200ms:
            - Track 0: filename=438ms, metadata=229ms (diff: ~200ms)
            - Track 1: filename=8339ms, metadata=8130ms (diff: ~200ms)

            Note: The ~200ms difference isn't crucial - either method works for alignment.
            Filename timestamps are preferable due to being better officially documented.

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
                start_time_seconds = extract_stream_start_time_from_container(
                    in_container, track_idx, logger=self.logger
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
                    apply_audio_padding_to_file(
                        in_container,
                        temp_path,
                        start_time_seconds,
                        track_idx,
                        logger=self.logger,
                    )

                    storage_path = (
                        f"file_pipeline/{transcript.id}/tracks/padded_{track_idx}.webm"
                    )

                    # Upload using file handle for streaming
                    with open(temp_path, "rb") as padded_file:
                        await storage.put_file(storage_path, padded_file)
                finally:
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

    async def mixdown_tracks(
        self,
        track_urls: list[str],
        writer: AudioFileWriterProcessor,
        offsets_seconds: list[float] | None = None,
    ) -> None:
        """Multi-track mixdown using PyAV filter graph (amix), reading from S3 presigned URLs."""
        target_sample_rate = detect_sample_rate_from_tracks(
            track_urls, logger=self.logger
        )
        if not target_sample_rate:
            self.logger.error("Mixdown failed - no decodable audio frames found")
            raise Exception("Mixdown failed: No decodable audio frames in any track")

        await mixdown_tracks_pyav(
            track_urls,
            writer,
            target_sample_rate,
            offsets_seconds=offsets_seconds,
            logger=self.logger,
        )

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

    async def update_participants_from_daily(
        self, transcript: Transcript, track_keys: list[str]
    ) -> None:
        """Update transcript participants with user_id and names from Daily.co API."""
        if not transcript.recording_id:
            return

        try:
            async with create_platform_client("daily") as daily_client:
                id_to_name = {}
                id_to_user_id = {}

                try:
                    rec_details = await daily_client.get_recording(
                        transcript.recording_id
                    )
                    mtg_session_id = rec_details.mtgSessionId
                    if mtg_session_id:
                        try:
                            payload: MeetingParticipantsResponse = (
                                await daily_client.get_meeting_participants(
                                    mtg_session_id
                                )
                            )
                            for p in payload.data:
                                pid = p.participant_id
                                name = p.user_name
                                user_id = p.user_id
                                if name:
                                    id_to_name[pid] = name
                                if user_id:
                                    id_to_user_id[pid] = user_id
                        except Exception as e:
                            self.logger.warning(
                                "Failed to fetch Daily meeting participants",
                                error=str(e),
                                mtg_session_id=mtg_session_id,
                                exc_info=True,
                            )
                    else:
                        self.logger.warning(
                            "No mtgSessionId found for recording; participant names may be generic",
                            recording_id=transcript.recording_id,
                        )
                except Exception as e:
                    self.logger.warning(
                        "Failed to fetch Daily recording details",
                        error=str(e),
                        recording_id=transcript.recording_id,
                        exc_info=True,
                    )
                    return

                cam_audio_keys = filter_cam_audio_tracks(track_keys)

                for idx, key in enumerate(cam_audio_keys):
                    try:
                        parsed = parse_daily_recording_filename(key)
                        participant_id = parsed.participant_id
                    except ValueError as e:
                        self.logger.error(
                            "Failed to parse Daily recording filename",
                            error=str(e),
                            key=key,
                            exc_info=True,
                        )
                        continue

                    default_name = f"Speaker {idx}"
                    name = id_to_name.get(participant_id, default_name)
                    user_id = id_to_user_id.get(participant_id)

                    participant = TranscriptParticipant(
                        id=participant_id, speaker=idx, name=name, user_id=user_id
                    )
                    await transcripts_controller.upsert_participant(
                        transcript, participant
                    )

        except Exception as e:
            self.logger.warning(
                "Failed to map participant names", error=str(e), exc_info=True
            )

    async def process(self, bucket_name: str, track_keys: list[str]):
        transcript = await self.get_transcript()
        async with self.transaction():
            await transcripts_controller.update(
                transcript,
                {
                    "events": [],
                    "topics": [],
                    "participants": [],
                },
            )

        await self.update_participants_from_daily(transcript, track_keys)

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
            on_action_items_callback=self.on_action_items,
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
