import os
import shutil
import subprocess
import threading
from typing import Generator

import faster_whisper
import librosa
import numpy as np
import torch
from fastapi import HTTPException
from silero_vad import VADIterator, load_silero_vad

from ..config import SAMPLE_RATE, VAD_CONFIG

# Whisper configuration (service-local defaults)
MODEL_NAME = "large-v2"
# None delegates compute type to runtime: float16 on CUDA, int8 on CPU
MODEL_COMPUTE_TYPE = None
MODEL_NUM_WORKERS = 1
CACHE_PATH = os.path.join(os.path.expanduser("~"), ".cache", "reflector-whisper")
from ..utils import NoStdStreams


class WhisperService:
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.lock = threading.Lock()

    def load(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = MODEL_COMPUTE_TYPE or (
            "float16" if self.device == "cuda" else "int8"
        )
        self.model = faster_whisper.WhisperModel(
            MODEL_NAME,
            device=self.device,
            compute_type=compute_type,
            num_workers=MODEL_NUM_WORKERS,
            download_root=CACHE_PATH,
        )

    def pad_audio(self, audio_array, sample_rate: int = SAMPLE_RATE):
        audio_duration = len(audio_array) / sample_rate
        if audio_duration < VAD_CONFIG["silence_padding"]:
            silence_samples = int(sample_rate * VAD_CONFIG["silence_padding"])
            silence = np.zeros(silence_samples, dtype=np.float32)
            return np.concatenate([audio_array, silence])
        return audio_array

    def enforce_word_timing_constraints(self, words: list[dict]) -> list[dict]:
        if len(words) <= 1:
            return words
        enforced: list[dict] = []
        for i, word in enumerate(words):
            current = dict(word)
            if i < len(words) - 1:
                next_start = words[i + 1]["start"]
                if current["end"] > next_start:
                    current["end"] = next_start
            enforced.append(current)
        return enforced

    def transcribe_file(self, file_path: str, language: str = "en") -> dict:
        input_for_model: str | "object" = file_path
        try:
            audio_array, _sample_rate = librosa.load(
                file_path, sr=SAMPLE_RATE, mono=True
            )
            if len(audio_array) / float(SAMPLE_RATE) < VAD_CONFIG["silence_padding"]:
                input_for_model = self.pad_audio(audio_array, SAMPLE_RATE)
        except Exception:
            pass

        with self.lock:
            with NoStdStreams():
                segments, _ = self.model.transcribe(
                    input_for_model,
                    language=language,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )

        segments = list(segments)
        text = "".join(segment.text for segment in segments).strip()
        words = [
            {
                "word": word.word,
                "start": round(float(word.start), 2),
                "end": round(float(word.end), 2),
            }
            for segment in segments
            for word in segment.words
        ]
        words = self.enforce_word_timing_constraints(words)
        return {"text": text, "words": words}

    def transcribe_vad_url_segment(
        self, file_path: str, timestamp_offset: float = 0.0, language: str = "en"
    ) -> dict:
        def load_audio_via_ffmpeg(input_path: str, sample_rate: int) -> np.ndarray:
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            cmd = [
                ffmpeg_bin,
                "-nostdin",
                "-threads",
                "1",
                "-i",
                input_path,
                "-f",
                "f32le",
                "-acodec",
                "pcm_f32le",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "pipe:1",
            ]
            try:
                proc = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"ffmpeg failed: {e}")
            audio = np.frombuffer(proc.stdout, dtype=np.float32)
            return audio

        # IMPORTANT: This VAD segment logic is duplicated in multiple files for deployment isolation.
        # If you modify this function, you MUST update all copies:
        #   - gpu/modal_deployments/reflector_transcriber.py
        #   - gpu/modal_deployments/reflector_transcriber_parakeet.py
        #   - gpu/self_hosted/app/services/transcriber.py (this file)
        def vad_segments(
            audio_array,
            sample_rate: int = SAMPLE_RATE,
            window_size: int = VAD_CONFIG["window_size"],
        ) -> Generator[tuple[float, float], None, None]:
            vad_model = load_silero_vad(onnx=False)
            iterator = VADIterator(vad_model, sampling_rate=sample_rate)
            start = None
            for i in range(0, len(audio_array), window_size):
                chunk = audio_array[i : i + window_size]
                if len(chunk) < window_size:
                    chunk = np.pad(
                        chunk, (0, window_size - len(chunk)), mode="constant"
                    )
                speech = iterator(chunk)
                if not speech:
                    continue
                if "start" in speech:
                    start = speech["start"]
                    continue
                if "end" in speech and start is not None:
                    end = speech["end"]
                    yield (start / float(SAMPLE_RATE), end / float(SAMPLE_RATE))
                    start = None
            # Handle case where audio ends while speech is still active
            if start is not None:
                audio_duration = len(audio_array) / float(sample_rate)
                yield (start / float(SAMPLE_RATE), audio_duration)
            iterator.reset_states()

        audio_array = load_audio_via_ffmpeg(file_path, SAMPLE_RATE)

        merged_batches: list[tuple[float, float]] = []
        batch_start = None
        batch_end = None
        max_duration = VAD_CONFIG["batch_max_duration"]
        for seg_start, seg_end in vad_segments(audio_array):
            if batch_start is None:
                batch_start, batch_end = seg_start, seg_end
                continue
            if seg_end - batch_start <= max_duration:
                batch_end = seg_end
            else:
                merged_batches.append((batch_start, batch_end))
                batch_start, batch_end = seg_start, seg_end
        if batch_start is not None and batch_end is not None:
            merged_batches.append((batch_start, batch_end))

        all_text = []
        all_words = []
        for start_time, end_time in merged_batches:
            s_idx = int(start_time * SAMPLE_RATE)
            e_idx = int(end_time * SAMPLE_RATE)
            segment = audio_array[s_idx:e_idx]
            segment = self.pad_audio(segment, SAMPLE_RATE)
            with self.lock:
                segments, _ = self.model.transcribe(
                    segment,
                    language=language,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )
            segments = list(segments)
            text = "".join(seg.text for seg in segments).strip()
            words = [
                {
                    "word": w.word,
                    "start": round(float(w.start) + start_time + timestamp_offset, 2),
                    "end": round(float(w.end) + start_time + timestamp_offset, 2),
                }
                for seg in segments
                for w in seg.words
            ]
            if text:
                all_text.append(text)
            all_words.extend(words)

        all_words = self.enforce_word_timing_constraints(all_words)
        return {"text": " ".join(all_text), "words": all_words}
