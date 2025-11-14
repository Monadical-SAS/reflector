import logging
import os
import sys
import threading
import uuid
from typing import Generator, Mapping, NamedTuple, NewType, TypedDict
from urllib.parse import urlparse

import modal

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"
SUPPORTED_FILE_EXTENSIONS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
SAMPLERATE = 16000
UPLOADS_PATH = "/uploads"
CACHE_PATH = "/cache"
VAD_CONFIG = {
    "batch_max_duration": 30.0,
    "silence_padding": 0.5,
    "window_size": 512,
}

ParakeetUniqFilename = NewType("ParakeetUniqFilename", str)
AudioFileExtension = NewType("AudioFileExtension", str)


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


app = modal.App("reflector-transcriber-parakeet")

# Volume for caching model weights
model_cache = modal.Volume.from_name("parakeet-model-cache", create_if_missing=True)
# Volume for temporary file uploads
upload_volume = modal.Volume.from_name("parakeet-uploads", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04", add_python="3.12"
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_HOME": "/cache",
            "DEBIAN_FRONTEND": "noninteractive",
            "CXX": "g++",
            "CC": "g++",
        }
    )
    .apt_install("ffmpeg")
    .pip_install(
        "hf_transfer==0.1.9",
        "huggingface_hub[hf-xet]==0.31.2",
        "nemo_toolkit[asr]==2.5.0",
        "cuda-python==12.8.0",
        "fastapi==0.115.12",
        "numpy<2",
        "librosa==0.10.1",
        "requests",
        "silero-vad==5.1.0",
        "torch",
    )
    .entrypoint([])  # silence chatty logs by container on start
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
) -> tuple[ParakeetUniqFilename, AudioFileExtension]:
    import requests
    from fastapi import HTTPException

    response = requests.head(audio_file_url, allow_redirects=True)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found")

    response = requests.get(audio_file_url, allow_redirects=True)
    response.raise_for_status()

    audio_suffix = detect_audio_format(audio_file_url, response.headers)
    unique_filename = ParakeetUniqFilename(f"{uuid.uuid4()}.{audio_suffix}")
    file_path = f"{UPLOADS_PATH}/{unique_filename}"

    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    return unique_filename, audio_suffix


def pad_audio(audio_array, sample_rate: int = SAMPLERATE):
    """Add 0.5 seconds of silence if audio is less than 500ms.

    This is a workaround for a Parakeet bug where very short audio (<500ms) causes:
    ValueError: `char_offsets`: [] and `processed_tokens`: [157, 834, 834, 841]
    have to be of the same length

    See: https://github.com/NVIDIA/NeMo/issues/8451
    """
    import numpy as np

    audio_duration = len(audio_array) / sample_rate
    if audio_duration < 0.5:
        silence_samples = int(sample_rate * 0.5)
        silence = np.zeros(silence_samples, dtype=np.float32)
        return np.concatenate([audio_array, silence])
    return audio_array


@app.cls(
    gpu="A10G",
    timeout=600,
    scaledown_window=300,
    image=image,
    volumes={CACHE_PATH: model_cache, UPLOADS_PATH: upload_volume},
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
@modal.concurrent(max_inputs=10)
class TranscriberParakeetLive:
    @modal.enter(snap=True)
    def enter(self):
        import nemo.collections.asr as nemo_asr

        logging.getLogger("nemo_logger").setLevel(logging.CRITICAL)

        self.lock = threading.Lock()
        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME)
        device = next(self.model.parameters()).device
        print(f"Model is on device: {device}")

    @modal.method()
    def transcribe_segment(
        self,
        filename: str,
    ):
        import librosa

        upload_volume.reload()

        file_path = f"{UPLOADS_PATH}/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array, sample_rate = librosa.load(file_path, sr=SAMPLERATE, mono=True)
        padded_audio = pad_audio(audio_array, sample_rate)

        with self.lock:
            with NoStdStreams():
                (output,) = self.model.transcribe([padded_audio], timestamps=True)

        text = output.text.strip()
        words: list[WordTiming] = [
            WordTiming(
                # XXX the space added here is to match the output of whisper
                # whisper add space to each words, while parakeet don't
                word=word_info["word"] + " ",
                start=round(word_info["start"], 2),
                end=round(word_info["end"], 2),
            )
            for word_info in output.timestamp["word"]
        ]

        return {"text": text, "words": words}

    @modal.method()
    def transcribe_batch(
        self,
        filenames: list[str],
    ):
        import librosa

        upload_volume.reload()

        results = []
        audio_arrays = []

        # Load all audio files with padding
        for filename in filenames:
            file_path = f"{UPLOADS_PATH}/{filename}"
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Batch file not found: {file_path}")

            audio_array, sample_rate = librosa.load(file_path, sr=SAMPLERATE, mono=True)
            padded_audio = pad_audio(audio_array, sample_rate)
            audio_arrays.append(padded_audio)

        with self.lock:
            with NoStdStreams():
                outputs = self.model.transcribe(audio_arrays, timestamps=True)

        # Process results for each file
        for i, (filename, output) in enumerate(zip(filenames, outputs)):
            text = output.text.strip()

            words: list[WordTiming] = [
                WordTiming(
                    word=word_info["word"] + " ",
                    start=round(word_info["start"], 2),
                    end=round(word_info["end"], 2),
                )
                for word_info in output.timestamp["word"]
            ]

            results.append(
                {
                    "filename": filename,
                    "text": text,
                    "words": words,
                }
            )

        return results


# L40S class for file transcription (bigger files)
@app.cls(
    gpu="L40S",
    timeout=900,
    image=image,
    volumes={CACHE_PATH: model_cache, UPLOADS_PATH: upload_volume},
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
class TranscriberParakeetFile:
    @modal.enter(snap=True)
    def enter(self):
        import nemo.collections.asr as nemo_asr
        import torch
        from silero_vad import load_silero_vad

        logging.getLogger("nemo_logger").setLevel(logging.CRITICAL)

        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME)
        device = next(self.model.parameters()).device
        print(f"Model is on device: {device}")

        torch.set_num_threads(1)
        self.vad_model = load_silero_vad(onnx=False)
        print("Silero VAD initialized")

    @modal.method()
    def transcribe_segment(
        self,
        filename: str,
        timestamp_offset: float = 0.0,
    ):
        import librosa
        import numpy as np
        from silero_vad import VADIterator

        def load_and_convert_audio(file_path):
            audio_array, sample_rate = librosa.load(file_path, sr=SAMPLERATE, mono=True)
            return audio_array

        def vad_segment_generator(
            audio_array,
        ) -> Generator[TimeSegment, None, None]:
            """Generate speech segments using VAD with start/end sample indices"""
            vad_iterator = VADIterator(self.vad_model, sampling_rate=SAMPLERATE)
            window_size = VAD_CONFIG["window_size"]
            start = None

            for i in range(0, len(audio_array), window_size):
                chunk = audio_array[i : i + window_size]
                if len(chunk) < window_size:
                    chunk = np.pad(
                        chunk, (0, window_size - len(chunk)), mode="constant"
                    )

                speech_dict = vad_iterator(chunk)
                if not speech_dict:
                    continue

                if "start" in speech_dict:
                    start = speech_dict["start"]
                    continue

                if "end" in speech_dict and start is not None:
                    end = speech_dict["end"]
                    start_time = start / float(SAMPLERATE)
                    end_time = end / float(SAMPLERATE)

                    yield TimeSegment(start_time, end_time)
                    start = None

            vad_iterator.reset_states()

        def batch_speech_segments(
            segments: Generator[TimeSegment, None, None], max_duration: int
        ) -> Generator[TimeSegment, None, None]:
            """
            Input segments:
              [0-2] [3-5] [6-8] [10-11] [12-15] [17-19] [20-22]

                                  ↓ (max_duration=10)

              Output batches:
              [0-8]           [10-19]          [20-22]

            Note: silences are kept for better transcription, previous implementation was
            passing segments separatly, but the output was less accurate.
            """
            batch_start_time = None
            batch_end_time = None

            for segment in segments:
                start_time, end_time = segment.start, segment.end
                if batch_start_time is None or batch_end_time is None:
                    batch_start_time = start_time
                    batch_end_time = end_time
                    continue

                total_duration = end_time - batch_start_time

                if total_duration <= max_duration:
                    batch_end_time = end_time
                    continue

                yield TimeSegment(batch_start_time, batch_end_time)
                batch_start_time = start_time
                batch_end_time = end_time

            if batch_start_time is None or batch_end_time is None:
                return

            yield TimeSegment(batch_start_time, batch_end_time)

        def batch_segment_to_audio_segment(
            segments: Generator[TimeSegment, None, None],
            audio_array,
        ) -> Generator[AudioSegment, None, None]:
            """Extract audio segments and apply padding for Parakeet compatibility.

            Uses pad_audio to ensure segments are at least 0.5s long, preventing
            Parakeet crashes. This padding may cause slight timing overlaps between
            segments, which are corrected by enforce_word_timing_constraints.
            """
            for segment in segments:
                start_time, end_time = segment.start, segment.end
                start_sample = int(start_time * SAMPLERATE)
                end_sample = int(end_time * SAMPLERATE)
                audio_segment = audio_array[start_sample:end_sample]

                padded_segment = pad_audio(audio_segment, SAMPLERATE)

                yield AudioSegment(start_time, end_time, padded_segment)

        def transcribe_batch(model, audio_segments: list) -> list:
            with NoStdStreams():
                outputs = model.transcribe(audio_segments, timestamps=True)
            return outputs

        def enforce_word_timing_constraints(
            words: list[WordTiming],
        ) -> list[WordTiming]:
            """Enforce that word end times don't exceed the start time of the next word.

            Due to silence padding added in batch_segment_to_audio_segment for better
            transcription accuracy, word timings from different segments may overlap.
            This function ensures there are no overlaps by adjusting end times.
            """
            if len(words) <= 1:
                return words

            enforced_words = []
            for i, word in enumerate(words):
                enforced_word = word.copy()

                if i < len(words) - 1:
                    next_start = words[i + 1]["start"]
                    if enforced_word["end"] > next_start:
                        enforced_word["end"] = next_start

                enforced_words.append(enforced_word)

            return enforced_words

        def emit_results(
            results: list,
            segments_info: list[AudioSegment],
        ) -> Generator[TranscriptResult, None, None]:
            """Yield transcribed text and word timings from model output, adjusting timestamps to absolute positions."""
            for i, (output, segment) in enumerate(zip(results, segments_info)):
                start_time, end_time = segment.start, segment.end
                text = output.text.strip()
                words: list[WordTiming] = [
                    WordTiming(
                        word=word_info["word"] + " ",
                        start=round(
                            word_info["start"] + start_time + timestamp_offset, 2
                        ),
                        end=round(word_info["end"] + start_time + timestamp_offset, 2),
                    )
                    for word_info in output.timestamp["word"]
                ]

                yield TranscriptResult(text, words)

        upload_volume.reload()

        file_path = f"{UPLOADS_PATH}/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array = load_and_convert_audio(file_path)
        total_duration = len(audio_array) / float(SAMPLERATE)

        all_text_parts: list[str] = []
        all_words: list[WordTiming] = []

        raw_segments = vad_segment_generator(audio_array)
        speech_segments = batch_speech_segments(
            raw_segments,
            VAD_CONFIG["batch_max_duration"],
        )
        audio_segments = batch_segment_to_audio_segment(speech_segments, audio_array)

        for batch in audio_segments:
            audio_segment = batch.audio
            results = transcribe_batch(self.model, [audio_segment])

            for result in emit_results(
                results,
                [batch],
            ):
                if not result.text:
                    continue
                all_text_parts.append(result.text)
                all_words.extend(result.words)

        all_words = enforce_word_timing_constraints(all_words)

        combined_text = " ".join(all_text_parts)
        return {"text": combined_text, "words": all_words}


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
    import os
    import uuid

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
    from pydantic import BaseModel

    transcriber_live = TranscriberParakeetLive()
    transcriber_file = TranscriberParakeetFile()

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

    class TranscriptResponse(BaseModel):
        result: dict

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(apikey_auth)])
    def transcribe(
        file: UploadFile = None,
        files: list[UploadFile] | None = None,
        model: str = Form(MODEL_NAME),
        language: str = Form("en"),
        batch: bool = Form(False),
    ):
        # Parakeet only supports English
        if language != "en":
            raise HTTPException(
                status_code=400,
                detail=f"Parakeet model only supports English. Got language='{language}'",
            )
        # Handle both single file and multiple files
        if not file and not files:
            raise HTTPException(
                status_code=400, detail="Either 'file' or 'files' parameter is required"
            )
        if batch and not files:
            raise HTTPException(
                status_code=400, detail="Batch transcription requires 'files'"
            )

        upload_files = [file] if file else files

        # Upload files to volume
        uploaded_filenames = []
        for upload_file in upload_files:
            audio_suffix = upload_file.filename.split(".")[-1]
            assert audio_suffix in SUPPORTED_FILE_EXTENSIONS

            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
            file_path = f"{UPLOADS_PATH}/{unique_filename}"

            print(f"Writing file to: {file_path}")
            with open(file_path, "wb") as f:
                content = upload_file.file.read()
                f.write(content)

            uploaded_filenames.append(unique_filename)

        upload_volume.commit()

        try:
            # Use A10G live transcriber for per-file transcription
            if batch and len(upload_files) > 1:
                # Use batch transcription
                func = transcriber_live.transcribe_batch.spawn(
                    filenames=uploaded_filenames,
                )
                results = func.get()
                return {"results": results}

            # Per-file transcription
            results = []
            for filename in uploaded_filenames:
                func = transcriber_live.transcribe_segment.spawn(
                    filename=filename,
                )
                result = func.get()
                result["filename"] = filename
                results.append(result)

            return {"results": results} if len(results) > 1 else results[0]

        finally:
            for filename in uploaded_filenames:
                try:
                    file_path = f"{UPLOADS_PATH}/{filename}"
                    print(f"Deleting file: {file_path}")
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")

            upload_volume.commit()

    @app.post("/v1/audio/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
    def transcribe_from_url(
        audio_file_url: str = Body(
            ..., description="URL of the audio file to transcribe"
        ),
        model: str = Body(MODEL_NAME),
        language: str = Body("en", description="Language code (only 'en' supported)"),
        timestamp_offset: float = Body(0.0),
    ):
        # Parakeet only supports English
        if language != "en":
            raise HTTPException(
                status_code=400,
                detail=f"Parakeet model only supports English. Got language='{language}'",
            )
        unique_filename, audio_suffix = download_audio_to_volume(audio_file_url)

        try:
            func = transcriber_file.transcribe_segment.spawn(
                filename=unique_filename,
                timestamp_offset=timestamp_offset,
            )
            result = func.get()
            return result
        finally:
            try:
                file_path = f"{UPLOADS_PATH}/{unique_filename}"
                print(f"Deleting file: {file_path}")
                os.remove(file_path)
                upload_volume.commit()
            except Exception as e:
                print(f"Error cleaning up {unique_filename}: {e}")

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
