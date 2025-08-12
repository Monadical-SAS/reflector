"""
Implementation using the GPU service from modal.com

API will be a POST request to TRANSCRIPT_URL:

```form
"timestamp": 123.456
"source_language": "en"
"target_language": "en"
"file": <audio file>
```

"""

from typing import List

import aiohttp
from openai import AsyncOpenAI

from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word
from reflector.settings import settings


class AudioTranscriptModalProcessor(AudioTranscriptProcessor):
    def __init__(
        self, modal_api_key: str | None = None, batch_enabled: bool = True, **kwargs
    ):
        super().__init__()
        if not settings.TRANSCRIPT_URL:
            raise Exception(
                "TRANSCRIPT_URL required to use AudioTranscriptModalProcessor"
            )
        self.transcript_url = settings.TRANSCRIPT_URL + "/v1"
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.modal_api_key = modal_api_key
        self.max_batch_duration = 10.0
        self.max_batch_files = 15
        self.batch_enabled = batch_enabled
        self.pending_files: List[AudioFile] = []  # Files waiting to be processed

    def _calculate_duration(self, audio_file: AudioFile) -> float:
        """Calculate audio duration in seconds from AudioFile metadata"""
        # Duration = total_samples / sample_rate
        # We need to estimate total samples from the file data
        import wave

        try:
            # Try to read as WAV file to get duration
            audio_file.fd.seek(0)
            with wave.open(audio_file.fd, "rb") as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate
                return duration
        except Exception:
            # Fallback: estimate from file size and audio parameters
            audio_file.fd.seek(0, 2)  # Seek to end
            file_size = audio_file.fd.tell()
            audio_file.fd.seek(0)  # Reset to beginning

            # Estimate: file_size / (sample_rate * channels * sample_width)
            bytes_per_second = (
                audio_file.sample_rate
                * audio_file.channels
                * (audio_file.sample_width // 8)
            )
            estimated_duration = (
                file_size / bytes_per_second if bytes_per_second > 0 else 0
            )
            return max(0, estimated_duration)

    def _create_batches(self, audio_files: List[AudioFile]) -> List[List[AudioFile]]:
        """Group audio files into batches with maximum 30s total duration"""
        batches = []
        current_batch = []
        current_duration = 0.0

        for audio_file in audio_files:
            duration = self._calculate_duration(audio_file)

            # If adding this file exceeds max duration, start a new batch
            if current_duration + duration > self.max_batch_duration and current_batch:
                batches.append(current_batch)
                current_batch = [audio_file]
                current_duration = duration
            else:
                current_batch.append(audio_file)
                current_duration += duration

        # Add the last batch if not empty
        if current_batch:
            batches.append(current_batch)

        return batches

    async def _transcript_batch(self, audio_files: List[AudioFile]) -> List[Transcript]:
        """Transcribe a batch of audio files using the parakeet backend"""
        if not audio_files:
            return []

        self.logger.debug(f"Batch transcribing {len(audio_files)} files")

        # Prepare form data for batch request
        data = aiohttp.FormData()
        data.add_field("language", self.get_pref("audio:source_language", "en"))
        data.add_field("batch", "true")

        for i, audio_file in enumerate(audio_files):
            audio_file.fd.seek(0)
            data.add_field(
                "files",
                audio_file.fd,
                filename=f"{audio_file.name}",
                content_type="audio/wav",
            )

        # Make batch request
        headers = {"Authorization": f"Bearer {self.modal_api_key}"}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(
                f"{self.transcript_url}/audio/transcriptions",
                data=data,
                headers=headers,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Batch transcription failed: {response.status} {error_text}"
                    )

                result = await response.json()

        # Process batch results
        transcripts = []
        results = result.get("results", [])

        for i, (audio_file, file_result) in enumerate(zip(audio_files, results)):
            transcript = Transcript(
                words=[
                    Word(
                        text=word_info["word"],
                        start=word_info["start"],
                        end=word_info["end"],
                    )
                    for word_info in file_result.get("words", [])
                ]
            )
            transcript.add_offset(audio_file.timestamp)
            transcripts.append(transcript)

        return transcripts

    async def _transcript(self, data: AudioFile):
        async with AsyncOpenAI(
            base_url=self.transcript_url,
            api_key=self.modal_api_key,
            timeout=self.timeout,
        ) as client:
            self.logger.debug(f"Try to transcribe audio {data.name}")

            audio_file = open(data.path, "rb")
            transcription = await client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                language=self.get_pref("audio:source_language", "en"),
                timestamp_granularities=["word"],
            )
            self.logger.debug(f"Transcription: {transcription}")
            transcript = Transcript(
                words=[
                    Word(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                    )
                    for word in transcription.words
                ],
            )
            transcript.add_offset(data.timestamp)

        return transcript

    async def transcript_multiple(
        self, audio_files: List[AudioFile]
    ) -> List[Transcript]:
        """Transcribe multiple audio files using batching"""
        if len(audio_files) == 1:
            # Single file, use existing method
            return [await self._transcript(audio_files[0])]

        # Create batches with max 30s duration each
        batches = self._create_batches(audio_files)

        self.logger.debug(
            f"Processing {len(audio_files)} files in {len(batches)} batches"
        )

        # Process all batches concurrently
        all_transcripts = []

        for batch in batches:
            batch_transcripts = await self._transcript_batch(batch)
            all_transcripts.extend(batch_transcripts)

        return all_transcripts

    async def _push(self, data: AudioFile):
        """Override _push to support batching"""
        if not self.batch_enabled:
            # Use parent implementation for single file processing
            return await super()._push(data)

        # Add file to pending batch
        self.pending_files.append(data)
        self.logger.debug(
            f"Added file to batch: {data.name}, batch size: {len(self.pending_files)}"
        )

        # Calculate total duration of pending files
        total_duration = sum(self._calculate_duration(f) for f in self.pending_files)

        # Process batch if it reaches max duration or has multiple files ready for optimization
        should_process_batch = (
            total_duration >= self.max_batch_duration
            or len(self.pending_files) >= self.max_batch_files
        )

        if should_process_batch:
            await self._process_pending_batch()

    async def _process_pending_batch(self):
        """Process all pending files as batches"""
        if not self.pending_files:
            return

        self.logger.debug(f"Processing batch of {len(self.pending_files)} files")

        try:
            # Create batches respecting duration limit
            batches = self._create_batches(self.pending_files)

            # Process each batch
            for batch in batches:
                self.m_transcript_call.inc()
                try:
                    with self.m_transcript.time():
                        # Use batch transcription
                        transcripts = await self._transcript_batch(batch)

                    self.m_transcript_success.inc()

                    # Emit each transcript
                    for transcript in transcripts:
                        if transcript:
                            await self.emit(transcript)

                except Exception:
                    self.m_transcript_failure.inc()
                    raise
                finally:
                    # Release audio files
                    for audio_file in batch:
                        audio_file.release()

        finally:
            # Clear pending files
            self.pending_files.clear()

    async def _flush(self):
        """Process any remaining files when flushing"""
        await self._process_pending_batch()
        await super()._flush()


AudioTranscriptAutoProcessor.register("modal", AudioTranscriptModalProcessor)
