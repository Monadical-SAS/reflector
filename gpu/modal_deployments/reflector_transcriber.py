import os
import sys
import threading
import uuid
from typing import Generator, Mapping, NamedTuple, NewType, TypedDict
from urllib.parse import urlparse

import modal

MODEL_NAME = "large-v2"
MODEL_COMPUTE_TYPE: str = "float16"
MODEL_NUM_WORKERS: int = 1
MINUTES = 60  # seconds
SAMPLERATE = 16000
UPLOADS_PATH = "/uploads"
CACHE_PATH = "/models"
SUPPORTED_FILE_EXTENSIONS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
VAD_CONFIG = {
    "batch_max_duration": 30.0,
    "silence_padding": 0.5,
    "window_size": 512,
}


WhisperUniqFilename = NewType("WhisperUniqFilename", str)
AudioFileExtension = NewType("AudioFileExtension", str)

app = modal.App("reflector-transcriber")

model_cache = modal.Volume.from_name("models", create_if_missing=True)
upload_volume = modal.Volume.from_name("whisper-uploads", create_if_missing=True)


class TimeSegment(NamedTuple):
    """Represents a time segment with start and end times."""

    start: float
    end: float


class AudioSegment(NamedTuple):
    """Represents an audio segment with timing and audio data."""

    start: float
    end: float
    audio: any


class TranscriptResult(NamedTuple):
    """Represents a transcription result with text and word timings."""

    text: str
    words: list["WordTiming"]


class WordTiming(TypedDict):
    """Represents a word with its timing information."""

    word: str
    start: float
    end: float


def download_model():
    from faster_whisper import download_model

    model_cache.reload()

    download_model(MODEL_NAME, cache_dir=CACHE_PATH)

    model_cache.commit()


image = (
    modal.Image.debian_slim(python_version="3.12")
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib/:"
                "/opt/conda/lib/python3.12/site-packages/nvidia/cublas/lib/"
            ),
        }
    )
    .apt_install("ffmpeg")
    .pip_install(
        "huggingface_hub==0.27.1",
        "hf-transfer==0.1.9",
        "torch==2.5.1",
        "faster-whisper==1.1.1",
        "fastapi==0.115.12",
        "python-multipart",
        "requests",
        "librosa==0.10.1",
        "numpy<2",
        "silero-vad==5.1.0",
    )
    .run_function(download_model, volumes={CACHE_PATH: model_cache})
)


def detect_audio_format(url: str, headers: Mapping[str, str]) -> AudioFileExtension:
    parsed_url = urlparse(url)
    url_path = parsed_url.path

    for ext in SUPPORTED_FILE_EXTENSIONS:
        if url_path.lower().endswith(f".{ext}"):
            return AudioFileExtension(ext)

    content_type = headers.get("content-type", "").lower()
    if "audio/mpeg" in content_type or "audio/mp3" in content_type:
        return AudioFileExtension("mp3")
    if "audio/wav" in content_type:
        return AudioFileExtension("wav")
    if "audio/mp4" in content_type:
        return AudioFileExtension("mp4")

    raise ValueError(
        f"Unsupported audio format for URL: {url}. "
        f"Supported extensions: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
    )


def download_audio_to_volume(
    audio_file_url: str,
) -> tuple[WhisperUniqFilename, AudioFileExtension]:
    import requests
    from fastapi import HTTPException

    response = requests.head(audio_file_url, allow_redirects=True)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found")

    response = requests.get(audio_file_url, allow_redirects=True)
    response.raise_for_status()

    audio_suffix = detect_audio_format(audio_file_url, response.headers)
    unique_filename = WhisperUniqFilename(f"{uuid.uuid4()}.{audio_suffix}")
    file_path = f"{UPLOADS_PATH}/{unique_filename}"

    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    return unique_filename, audio_suffix


def pad_audio(audio_array, sample_rate: int = SAMPLERATE):
    """Add 0.5s of silence if audio is shorter than the silence_padding window.

    Whisper does not require this strictly, but aligning behavior with Parakeet
    avoids edge-case crashes on extremely short inputs and makes comparisons easier.
    """
    import numpy as np

    audio_duration = len(audio_array) / sample_rate
    if audio_duration < VAD_CONFIG["silence_padding"]:
        silence_samples = int(sample_rate * VAD_CONFIG["silence_padding"])
        silence = np.zeros(silence_samples, dtype=np.float32)
        return np.concatenate([audio_array, silence])
    return audio_array


@app.cls(
    gpu="A10G",
    timeout=5 * MINUTES,
    scaledown_window=5 * MINUTES,
    image=image,
    volumes={CACHE_PATH: model_cache, UPLOADS_PATH: upload_volume},
)
@modal.concurrent(max_inputs=10)
class TranscriberWhisperLive:
    """Live transcriber class for small audio segments (A10G).

    Mirrors the Parakeet live class API but uses Faster-Whisper under the hood.
    """

    @modal.enter()
    def enter(self):
        import faster_whisper
        import torch

        self.lock = threading.Lock()
        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            MODEL_NAME,
            device=self.device,
            compute_type=MODEL_COMPUTE_TYPE,
            num_workers=MODEL_NUM_WORKERS,
            download_root=CACHE_PATH,
            local_files_only=True,
        )
        print(f"Model is on device: {self.device}")

    @modal.method()
    def transcribe_segment(
        self,
        filename: str,
        language: str = "en",
    ):
        """Transcribe a single uploaded audio file by filename."""
        upload_volume.reload()

        file_path = f"{UPLOADS_PATH}/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with self.lock:
            with NoStdStreams():
                segments, _ = self.model.transcribe(
                    file_path,
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

        return {"text": text, "words": words}

    @modal.method()
    def transcribe_batch(
        self,
        filenames: list[str],
        language: str = "en",
    ):
        """Transcribe multiple uploaded audio files and return per-file results."""
        upload_volume.reload()

        results = []
        for filename in filenames:
            file_path = f"{UPLOADS_PATH}/{filename}"
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Batch file not found: {file_path}")

            with self.lock:
                with NoStdStreams():
                    segments, _ = self.model.transcribe(
                        file_path,
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
                    "start": round(float(w.start), 2),
                    "end": round(float(w.end), 2),
                }
                for seg in segments
                for w in seg.words
            ]

            results.append(
                {
                    "filename": filename,
                    "text": text,
                    "words": words,
                }
            )

        return results


@app.cls(
    gpu="L40S",
    timeout=15 * MINUTES,
    image=image,
    volumes={CACHE_PATH: model_cache, UPLOADS_PATH: upload_volume},
)
class TranscriberWhisperFile:
    """File transcriber for larger/longer audio, using VAD-driven batching (L40S)."""

    @modal.enter()
    def enter(self):
        import faster_whisper
        import torch
        from silero_vad import load_silero_vad

        self.lock = threading.Lock()
        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            MODEL_NAME,
            device=self.device,
            compute_type=MODEL_COMPUTE_TYPE,
            num_workers=MODEL_NUM_WORKERS,
            download_root=CACHE_PATH,
            local_files_only=True,
        )
        self.vad_model = load_silero_vad(onnx=False)

    @modal.method()
    def transcribe_segment(
        self, filename: str, timestamp_offset: float = 0.0, language: str = "en"
    ):
        import librosa
        import numpy as np
        from silero_vad import VADIterator

        def vad_segments(
            audio_array,
            sample_rate: int = SAMPLERATE,
            window_size: int = VAD_CONFIG["window_size"],
        ) -> Generator[TimeSegment, None, None]:
            """Generate speech segments as TimeSegment using Silero VAD."""
            iterator = VADIterator(self.vad_model, sampling_rate=sample_rate)
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
                    yield TimeSegment(
                        start / float(SAMPLERATE), end / float(SAMPLERATE)
                    )
                    start = None
            iterator.reset_states()

        upload_volume.reload()
        file_path = f"{UPLOADS_PATH}/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array, _sr = librosa.load(file_path, sr=SAMPLERATE, mono=True)

        # Batch segments up to ~30s windows by merging contiguous VAD segments
        merged_batches: list[TimeSegment] = []
        batch_start = None
        batch_end = None
        max_duration = VAD_CONFIG["batch_max_duration"]
        for segment in vad_segments(audio_array):
            seg_start, seg_end = segment.start, segment.end
            if batch_start is None:
                batch_start, batch_end = seg_start, seg_end
                continue
            if seg_end - batch_start <= max_duration:
                batch_end = seg_end
            else:
                merged_batches.append(TimeSegment(batch_start, batch_end))
                batch_start, batch_end = seg_start, seg_end
        if batch_start is not None and batch_end is not None:
            merged_batches.append(TimeSegment(batch_start, batch_end))

        all_text = []
        all_words = []

        for segment in merged_batches:
            start_time, end_time = segment.start, segment.end
            s_idx = int(start_time * SAMPLERATE)
            e_idx = int(end_time * SAMPLERATE)
            segment = audio_array[s_idx:e_idx]
            segment = pad_audio(segment, SAMPLERATE)

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

        return {"text": " ".join(all_text), "words": all_words}


def detect_audio_format(url: str, headers: dict) -> str:
    from urllib.parse import urlparse

    from fastapi import HTTPException

    url_path = urlparse(url).path
    for ext in SUPPORTED_FILE_EXTENSIONS:
        if url_path.lower().endswith(f".{ext}"):
            return ext

    content_type = headers.get("content-type", "").lower()
    if "audio/mpeg" in content_type or "audio/mp3" in content_type:
        return "mp3"
    if "audio/wav" in content_type:
        return "wav"
    if "audio/mp4" in content_type:
        return "mp4"

    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported audio format for URL. Supported extensions: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
        ),
    )


def download_audio_to_volume(audio_file_url: str) -> tuple[str, str]:
    import requests
    from fastapi import HTTPException

    response = requests.head(audio_file_url, allow_redirects=True)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found")

    response = requests.get(audio_file_url, allow_redirects=True)
    response.raise_for_status()

    audio_suffix = detect_audio_format(audio_file_url, response.headers)
    unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
    file_path = f"{UPLOADS_PATH}/{unique_filename}"

    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    return unique_filename, audio_suffix


@app.function(
    scaledown_window=60,
    timeout=600,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={CACHE_PATH: model_cache, UPLOADS_PATH: upload_volume},
    image=image,
)
@modal.concurrent(max_inputs=40)
@modal.asgi_app()
def web():
    from fastapi import (
        Body,
        Depends,
        FastAPI,
        Form,
        HTTPException,
        UploadFile,
        status,
    )
    from fastapi.security import OAuth2PasswordBearer

    transcriber_live = TranscriberWhisperLive()
    transcriber_file = TranscriberWhisperFile()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey == os.environ["REFLECTOR_GPU_APIKEY"]:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    class TranscriptResponse(dict):
        pass

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(apikey_auth)])
    def transcribe(
        file: UploadFile = None,
        files: list[UploadFile] | None = None,
        model: str = Form(MODEL_NAME),
        language: str = Form("en"),
        batch: bool = Form(False),
    ):
        if not file and not files:
            raise HTTPException(
                status_code=400, detail="Either 'file' or 'files' parameter is required"
            )
        if batch and not files:
            raise HTTPException(
                status_code=400, detail="Batch transcription requires 'files'"
            )

        upload_files = [file] if file else files

        uploaded_filenames: list[str] = []
        for upload_file in upload_files:
            audio_suffix = upload_file.filename.split(".")[-1]
            if audio_suffix not in SUPPORTED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported audio format. Supported extensions: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
                    ),
                )

            unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
            file_path = f"{UPLOADS_PATH}/{unique_filename}"
            with open(file_path, "wb") as f:
                content = upload_file.file.read()
                f.write(content)
            uploaded_filenames.append(unique_filename)

        upload_volume.commit()

        try:
            if batch and len(upload_files) > 1:
                func = transcriber_live.transcribe_batch.spawn(
                    filenames=uploaded_filenames,
                    language=language,
                )
                results = func.get()
                return {"results": results}

            results = []
            for filename in uploaded_filenames:
                func = transcriber_live.transcribe_segment.spawn(
                    filename=filename,
                    language=language,
                )
                result = func.get()
                result["filename"] = filename
                results.append(result)

            return {"results": results} if len(results) > 1 else results[0]
        finally:
            for filename in uploaded_filenames:
                try:
                    file_path = f"{UPLOADS_PATH}/{filename}"
                    os.remove(file_path)
                except Exception:
                    pass
            upload_volume.commit()

    @app.post("/v1/audio/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
    def transcribe_from_url(
        audio_file_url: str = Body(
            ..., description="URL of the audio file to transcribe"
        ),
        model: str = Body(MODEL_NAME),
        language: str = Body("en"),
        timestamp_offset: float = Body(0.0),
    ):
        unique_filename, _audio_suffix = download_audio_to_volume(audio_file_url)
        try:
            func = transcriber_file.transcribe_segment.spawn(
                filename=unique_filename,
                timestamp_offset=timestamp_offset,
                language=language,
            )
            result = func.get()
            return result
        finally:
            try:
                file_path = f"{UPLOADS_PATH}/{unique_filename}"
                os.remove(file_path)
                upload_volume.commit()
            except Exception:
                pass

    return app


class NoStdStreams:
    def __init__(self):
        self.devnull = open(os.devnull, "w")

    def __enter__(self):
        self._stdout, self._stderr = sys.stdout, sys.stderr
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout, sys.stderr = self.devnull, self.devnull

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout, sys.stderr = self._stdout, self._stderr
        self.devnull.close()
