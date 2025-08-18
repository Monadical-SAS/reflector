import logging
import os
import sys
import threading
import uuid
from typing import Mapping, NewType

import modal

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"
SUPPORTED_FILE_EXTENSIONS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
SAMPLERATE = 16000
VAD_CONFIG = {
    "max_segment_duration": 30.0,
    "batch_max_files": 10,
    "batch_max_duration": 5.0,
    "min_segment_duration": 0.02,
    "silence_padding": 0.5,
    "window_size": 512,
}

ParakeetUniqFilename = NewType("ParakeetUniqFilename", str)
AudioFileExtension = NewType("AudioFileExtension", str)

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
        "nemo_toolkit[asr]==2.3.0",
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
    for ext in SUPPORTED_FILE_EXTENSIONS:
        if url.lower().endswith(f".{ext}"):
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
    file_path = f"/uploads/{unique_filename}"

    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    return unique_filename, audio_suffix


def pad_audio(audio_array, sample_rate=SAMPLERATE):
    """Add 0.5 seconds of silence if audio is less than 500ms"""
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
    volumes={"/cache": model_cache, "/uploads": upload_volume},
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
        language: str,
    ):
        import librosa

        upload_volume.reload()

        file_path = f"/uploads/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array, sample_rate = librosa.load(file_path, sr=SAMPLERATE, mono=True)
        padded_audio = pad_audio(audio_array, sample_rate)

        with self.lock:
            with NoStdStreams():
                (output,) = self.model.transcribe([padded_audio], timestamps=True)

        text = output.text.strip()
        words = [
            {
                "word": word_info["word"],
                "start": round(word_info["start"], 2),
                "end": round(word_info["end"], 2),
            }
            for word_info in output.timestamp["word"]
        ]

        return {"text": text, "words": words}

    @modal.method()
    def transcribe_batch(
        self,
        filenames: list[str],
        language: str,
    ):
        import librosa

        upload_volume.reload()

        results = []
        audio_arrays = []

        # Load all audio files with padding
        for filename in filenames:
            file_path = f"/uploads/{filename}"
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
            words = []

            words = [
                {
                    "word": word_info["word"],
                    "start": round(word_info["start"], 2),
                    "end": round(word_info["end"], 2),
                }
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
    volumes={"/cache": model_cache, "/uploads": upload_volume},
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
        language: str,
        timestamp_offset: float = 0.0,
    ):
        import librosa
        import numpy as np
        from silero_vad import VADIterator

        def load_and_convert_audio(file_path):
            audio_array, sample_rate = librosa.load(file_path, sr=SAMPLERATE, mono=True)
            return audio_array

        def vad_segment_generator(audio_array):
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

                    # Extract the actual audio segment
                    audio_segment = audio_array[start:end]

                    yield (start_time, end_time, audio_segment)
                    start = None

            vad_iterator.reset_states()

        def vad_segment_filter(segments):
            """Filter VAD segments by duration and chunk large segments"""
            min_dur = VAD_CONFIG["min_segment_duration"]
            max_dur = VAD_CONFIG["max_segment_duration"]

            for start_time, end_time, audio_segment in segments:
                segment_duration = end_time - start_time

                # Skip very small segments
                if segment_duration < min_dur:
                    continue

                # If segment is within max duration, yield as-is
                if segment_duration <= max_dur:
                    yield (start_time, end_time, audio_segment)
                    continue

                # Chunk large segments into smaller pieces
                chunk_samples = int(max_dur * SAMPLERATE)
                current_start = start_time

                for chunk_offset in range(0, len(audio_segment), chunk_samples):
                    chunk_audio = audio_segment[
                        chunk_offset : chunk_offset + chunk_samples
                    ]
                    if len(chunk_audio) == 0:
                        break

                    chunk_duration = len(chunk_audio) / float(SAMPLERATE)
                    chunk_end = current_start + chunk_duration

                    # Only yield chunks that meet minimum duration
                    if chunk_duration >= min_dur:
                        yield (current_start, chunk_end, chunk_audio)

                    current_start = chunk_end

        def batch_segments(segments, max_files=10, max_duration=5.0):
            batch = []
            batch_duration = 0.0

            for start_time, end_time, audio_segment in segments:
                segment_duration = end_time - start_time

                if segment_duration < VAD_CONFIG["silence_padding"]:
                    silence_samples = int(
                        (VAD_CONFIG["silence_padding"] - segment_duration) * SAMPLERATE
                    )
                    padding = np.zeros(silence_samples, dtype=np.float32)
                    audio_segment = np.concatenate([audio_segment, padding])
                    segment_duration = VAD_CONFIG["silence_padding"]

                batch.append((start_time, end_time, audio_segment))
                batch_duration += segment_duration

                if len(batch) >= max_files or batch_duration >= max_duration:
                    yield batch
                    batch = []
                    batch_duration = 0.0

            if batch:
                yield batch

        def transcribe_batch(model, audio_segments):
            with NoStdStreams():
                outputs = model.transcribe(audio_segments, timestamps=True)
            return outputs

        def emit_results(
            results,
            segments_info,
            batch_index,
            total_batches,
        ):
            for i, (output, (start_time, end_time, _)) in enumerate(
                zip(results, segments_info)
            ):
                text = output.text.strip()
                words = []

                if (
                    hasattr(output, "timestamp")
                    and output.timestamp
                    and "word" in output.timestamp
                ):
                    words = [
                        {
                            "word": word_info["word"],
                            "start": round(
                                word_info["start"] + start_time + timestamp_offset, 2
                            ),
                            "end": round(
                                word_info["end"] + start_time + timestamp_offset, 2
                            ),
                        }
                        for word_info in output.timestamp["word"]
                    ]

                yield text, words

        upload_volume.reload()

        file_path = f"/uploads/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array = load_and_convert_audio(file_path)
        total_duration = len(audio_array) / float(SAMPLERATE)
        processed_duration = 0.0

        all_text_parts = []
        all_words = []

        raw_segments = vad_segment_generator(audio_array)
        filtered_segments = vad_segment_filter(raw_segments)
        batches = batch_segments(
            filtered_segments,
            VAD_CONFIG["batch_max_files"],
            VAD_CONFIG["batch_max_duration"],
        )

        batch_index = 0
        total_batches = max(
            1, int(total_duration / VAD_CONFIG["batch_max_duration"]) + 1
        )

        for batch in batches:
            batch_index += 1
            audio_segments = [seg[2] for seg in batch]
            results = transcribe_batch(self.model, audio_segments)

            for text, words in emit_results(
                results,
                batch,
                batch_index,
                total_batches,
            ):
                if not text:
                    continue
                all_text_parts.append(text)
                all_words.extend(words)

            processed_duration += sum(len(seg[2]) / float(SAMPLERATE) for seg in batch)

        combined_text = " ".join(all_text_parts)
        return {"text": combined_text, "words": all_words}


@app.function(
    scaledown_window=60,
    timeout=600,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={"/cache": model_cache, "/uploads": upload_volume},
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
            assert audio_suffix in SUPPORTED_FILE_TYPES

            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
            file_path = f"/uploads/{unique_filename}"

            print(f"Writing file to: {file_path}")
            with open(file_path, "wb") as f:
                content = upload_file.file.read()
                f.write(content)

            uploaded_filenames.append(unique_filename)

        upload_volume.commit()

        try:
            # Use A10G live transcriber for small files
            if batch and len(upload_files) > 1:
                # Use batch transcription
                func = transcriber_live.transcribe_batch.spawn(
                    filenames=uploaded_filenames,
                    language=language,
                )
                results = func.get()
                return {"results": results}

            # Single file transcription
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
                    file_path = f"/uploads/{filename}"
                    print(f"Deleting file: {file_path}")
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")

            upload_volume.commit()

    @app.post("/v1/audio/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
    def transcribe_from_url(
        audio_file_url: str = Body(...),
        model: str = Body(MODEL_NAME),
        language: str = Body("en"),
        timestamp_offset: float = Body(0.0),
    ):
        unique_filename, audio_suffix = download_audio_to_volume(audio_file_url)

        try:
            func = transcriber_file.transcribe_segment.spawn(
                filename=unique_filename,
                language=language,
                timestamp_offset=timestamp_offset,
            )
            result = func.get()
            return result
        finally:
            try:
                file_path = f"/uploads/{unique_filename}"
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
