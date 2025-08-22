from typing import Optional

import av
import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

from reflector.processors.audio_chunker import AudioChunkerProcessor
from reflector.processors.audio_chunker_auto import AudioChunkerAutoProcessor


class AudioChunkerSileroProcessor(AudioChunkerProcessor):
    """
    Assemble audio frames into chunks with VAD-based speech detection using Silero VAD
    """

    def __init__(
        self,
        block_frames=256,
        max_frames=1024,
        use_onnx=True,
        min_frames=2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.block_frames = block_frames
        self.max_frames = max_frames
        self.min_frames = min_frames

        # Initialize Silero VAD
        self._init_vad(use_onnx)

    def _init_vad(self, use_onnx=False):
        """Initialize Silero VAD model"""
        try:
            torch.set_num_threads(1)
            self.vad_model = load_silero_vad(onnx=use_onnx)
            self.vad_iterator = VADIterator(self.vad_model, sampling_rate=16000)
            self.logger.info("Silero VAD initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Silero VAD: {e}")
            self.vad_model = None
            self.vad_iterator = None

    async def _chunk(self, data: av.AudioFrame) -> Optional[list[av.AudioFrame]]:
        """Process audio frame and return chunk when ready"""
        self.frames.append(data)

        # Check for speech segments every 32 frames (~1 second)
        if len(self.frames) >= 32 and len(self.frames) % 32 == 0:
            return await self._process_block()

        # Safety fallback - emit if we hit max frames
        elif len(self.frames) >= self.max_frames:
            self.logger.warning(
                f"AudioChunkerSileroProcessor: Reached max frames ({self.max_frames}), "
                f"emitting first {self.max_frames // 2} frames"
            )
            frames_to_emit = self.frames[: self.max_frames // 2]
            self.frames = self.frames[self.max_frames // 2 :]
            if len(frames_to_emit) >= self.min_frames:
                return frames_to_emit
            else:
                self.logger.debug(
                    f"Ignoring fallback segment with {len(frames_to_emit)} frames "
                    f"(< {self.min_frames} minimum)"
                )

        return None

    async def _process_block(self) -> Optional[list[av.AudioFrame]]:
        # Need at least 32 frames for VAD detection (~1 second)
        if len(self.frames) < 32 or self.vad_iterator is None:
            return None

        # Processing block with current buffer size
        print(f"Processing block: {len(self.frames)} frames in buffer")

        try:
            # Convert frames to numpy array for VAD
            audio_array = self._frames_to_numpy(self.frames)

            if audio_array is None:
                # Fallback: emit all frames if conversion failed
                frames_to_emit = self.frames[:]
                self.frames = []
                if len(frames_to_emit) >= self.min_frames:
                    return frames_to_emit
                else:
                    self.logger.debug(
                        f"Ignoring conversion-failed segment with {len(frames_to_emit)} frames "
                        f"(< {self.min_frames} minimum)"
                    )
                return None

            # Find complete speech segments in the buffer
            speech_end_frame = self._find_speech_segment_end(audio_array)

            if speech_end_frame is None or speech_end_frame <= 0:
                # No speech found but buffer is getting large
                if len(self.frames) > 512:
                    # Check if it's all silence and can be discarded
                    # No speech segment found, buffer at {len(self.frames)} frames

                    # Could emit silence or discard old frames here
                    # For now, keep first 256 frames and discard older silence
                    if len(self.frames) > 768:
                        self.logger.debug(
                            f"Discarding {len(self.frames) - 256} old frames (likely silence)"
                        )
                        self.frames = self.frames[-256:]
                return None

            # Calculate segment timing information
            frames_to_emit = self.frames[:speech_end_frame]

            # Get timing from av.AudioFrame
            if frames_to_emit:
                first_frame = frames_to_emit[0]
                last_frame = frames_to_emit[-1]
                sample_rate = first_frame.sample_rate

                # Calculate duration
                total_samples = sum(f.samples for f in frames_to_emit)
                duration_seconds = total_samples / sample_rate if sample_rate > 0 else 0

                # Get timestamps if available
                start_time = (
                    first_frame.pts * first_frame.time_base if first_frame.pts else 0
                )
                end_time = (
                    last_frame.pts * last_frame.time_base if last_frame.pts else 0
                )

                # Convert to HH:MM:SS format for logging
                def format_time(seconds):
                    if not seconds:
                        return "00:00:00"
                    total_seconds = int(float(seconds))
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    secs = total_seconds % 60
                    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

                start_formatted = format_time(start_time)
                end_formatted = format_time(end_time)

                # Keep remaining frames for next processing
                remaining_after = len(self.frames) - speech_end_frame

                # Single structured log line
                self.logger.info(
                    "Speech segment found",
                    start=start_formatted,
                    end=end_formatted,
                    frames=speech_end_frame,
                    duration=round(duration_seconds, 2),
                    buffer_before=len(self.frames),
                    remaining=remaining_after,
                )

            # Keep remaining frames for next processing
            self.frames = self.frames[speech_end_frame:]

            # Filter out segments with too few frames
            if len(frames_to_emit) >= self.min_frames:
                return frames_to_emit
            else:
                self.logger.debug(
                    f"Ignoring segment with {len(frames_to_emit)} frames "
                    f"(< {self.min_frames} minimum)"
                )

        except Exception as e:
            self.logger.error(f"Error in VAD processing: {e}")
            # Fallback to simple chunking
            if len(self.frames) >= self.block_frames:
                frames_to_emit = self.frames[: self.block_frames]
                self.frames = self.frames[self.block_frames :]
                if len(frames_to_emit) >= self.min_frames:
                    return frames_to_emit
                else:
                    self.logger.debug(
                        f"Ignoring exception-fallback segment with {len(frames_to_emit)} frames "
                        f"(< {self.min_frames} minimum)"
                    )

        return None

    def _frames_to_numpy(self, frames: list[av.AudioFrame]) -> Optional[np.ndarray]:
        """Convert av.AudioFrame list to numpy array for VAD processing"""
        if not frames:
            return None

        try:
            audio_data = []
            for frame in frames:
                frame_array = frame.to_ndarray()

                if len(frame_array.shape) == 2:
                    frame_array = frame_array.flatten()

                audio_data.append(frame_array)

            if not audio_data:
                return None

            combined_audio = np.concatenate(audio_data)

            # Ensure float32 format
            if combined_audio.dtype == np.int16:
                # Normalize int16 audio to float32 in range [-1.0, 1.0]
                combined_audio = combined_audio.astype(np.float32) / 32768.0
            elif combined_audio.dtype != np.float32:
                combined_audio = combined_audio.astype(np.float32)

            return combined_audio

        except Exception as e:
            self.logger.error(f"Error converting frames to numpy: {e}")

        return None

    def _find_speech_segment_end(self, audio_array: np.ndarray) -> Optional[int]:
        """Find complete speech segments and return frame index at segment end"""
        if self.vad_iterator is None or len(audio_array) == 0:
            return None

        try:
            # Process audio in 512-sample windows for VAD
            window_size = 512
            min_silence_windows = 3  # Require 3 windows of silence after speech

            # Track speech state
            in_speech = False
            speech_start = None
            speech_end = None
            silence_count = 0

            for i in range(0, len(audio_array), window_size):
                chunk = audio_array[i : i + window_size]
                if len(chunk) < window_size:
                    chunk = np.pad(chunk, (0, window_size - len(chunk)))

                # Detect if this window has speech
                speech_dict = self.vad_iterator(chunk, return_seconds=True)

                # VADIterator returns dict with 'start' and 'end' when speech segments are detected
                if speech_dict:
                    if not in_speech:
                        # Speech started
                        speech_start = i
                        in_speech = True
                        # Debug: print(f"Speech START at sample {i}, VAD: {speech_dict}")
                    silence_count = 0  # Reset silence counter
                    continue

                if not in_speech:
                    continue

                # We're in speech but found silence
                silence_count += 1
                if silence_count < min_silence_windows:
                    continue

                # Found end of speech segment
                speech_end = i - (min_silence_windows - 1) * window_size
                # Debug: print(f"Speech END at sample {speech_end}")

                # Convert sample position to frame index
                samples_per_frame = self.frames[0].samples if self.frames else 1024
                frame_index = speech_end // samples_per_frame

                # Ensure we don't exceed buffer
                frame_index = min(frame_index, len(self.frames))
                return frame_index

            return None

        except Exception as e:
            self.logger.error(f"Error finding speech segment: {e}")
            return None

    async def _flush(self):
        frames = self.frames[:]
        self.frames = []
        if frames:
            if len(frames) >= self.min_frames:
                await self.emit(frames)
            else:
                self.logger.debug(
                    f"Ignoring flush segment with {len(frames)} frames "
                    f"(< {self.min_frames} minimum)"
                )


AudioChunkerAutoProcessor.register("silero", AudioChunkerSileroProcessor)
