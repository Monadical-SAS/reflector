import json
import logging
import os
import sys
import threading
import uuid

import modal
from pydantic import BaseModel

# Volume for caching model weights
model_cache = modal.Volume.from_name("parakeet-model-cache", create_if_missing=True)
# Volume for temporary file uploads
upload_volume = modal.Volume.from_name("parakeet-uploads", create_if_missing=True)

# App configuration
app = modal.App("reflector-transcriber-parakeet")

MINUTES = 60  # seconds

# Image configuration
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04", add_python="3.12"
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_HOME": "/cache",  # cache directory for Hugging Face models
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
        "pydub==0.25.1",
        "silero-vad==5.1.0",
        "torch",
    )
    .entrypoint([])  # silence chatty logs by container on start
)


def detect_audio_format(url: str, headers: dict) -> str:
    supported_file_types = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

    url_lower = url.lower()
    for ext in supported_file_types:
        if url_lower.endswith(f".{ext}"):
            return ext

    content_type = headers.get("content-type", "").lower()
    if "audio/mpeg" in content_type or "audio/mp3" in content_type:
        return "mp3"
    elif "audio/wav" in content_type:
        return "wav"
    elif "audio/mp4" in content_type:
        return "mp4"

    return "mp3"


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
    file_path = f"/uploads/{unique_filename}"

    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    return unique_filename, audio_suffix


@app.cls(
    # gpu="A10G",
    gpu="L40S",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    image=image,
    volumes={"/cache": model_cache, "/uploads": upload_volume},
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
@modal.concurrent(max_inputs=6)
class TranscriberParakeet:
    @modal.enter(snap=True)
    def enter(self):
        import nemo.collections.asr as nemo_asr
        import torch
        from silero_vad import load_silero_vad

        logging.getLogger("nemo_logger").setLevel(logging.CRITICAL)

        self.lock = threading.Lock()
        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v2"
        )
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
    ):
        import os

        import librosa
        import numpy as np

        # Reload volume to see new files
        upload_volume.reload()

        # List files to debug
        files = os.listdir("/uploads")
        print(f"Files in /uploads after reload: {files}")

        # Load audio from volume
        file_path = f"/uploads/{filename}"
        print(f"Looking for file: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load audio using librosa (NeMo's preferred method)
        audio_array, sample_rate = librosa.load(file_path, sr=16000, mono=True)

        # Add 1 second of silence after the audio to help with timestamp computation
        silence_samples = int(sample_rate * 1.0)  # 1 second of silence
        silence = np.zeros(silence_samples, dtype=np.float32)
        padded_audio = np.concatenate([audio_array, silence])

        with self.lock:
            # Use NoStdStreams context manager to silence output
            with NoStdStreams():
                output = self.model.transcribe([padded_audio], timestamps=True)

        text = output[0].text.strip()
        words = []

        # Extract word timestamps (no adjustment needed since padding is after audio)
        if (
            hasattr(output[0], "timestamp")
            and output[0].timestamp
            and "word" in output[0].timestamp
        ):
            words = [
                {
                    "word": word_info["word"],
                    "start": round(word_info["start"], 2),
                    "end": round(word_info["end"], 2),
                }
                for word_info in output[0].timestamp["word"]
            ]

        return {"text": text, "words": words}

    @modal.method()
    def transcribe_segment_with_offset(
        self,
        filename: str,
        language: str,
        timestamp_offset: float = 0.0,
        progress_queue: modal.Queue | None = None,
    ):
        import os

        import numpy as np
        from pydub import AudioSegment
        from silero_vad import VADIterator

        VAD_CONFIG = {
            "max_segment_duration": 30.0,
            "batch_max_files": 10,
            "batch_max_duration": 5.0,
            "min_segment_duration": 0.02,
            "silence_padding": 0.5,
            "window_size": 512,
        }

        def load_and_convert_audio(file_path):
            if filename.lower().endswith(".mp3"):
                audio = AudioSegment.from_mp3(file_path)
            elif filename.lower().endswith(".wav"):
                audio = AudioSegment.from_wav(file_path)
            else:
                audio = AudioSegment.from_file(file_path)

            audio = audio.set_frame_rate(16000).set_channels(1)
            audio_array = np.frombuffer(audio.raw_data, dtype=np.int16).astype(
                np.float32
            )
            return audio_array / 32768.0

        def vad_segment_generator(audio_array, max_duration=30.0):
            vad_iterator = VADIterator(self.vad_model, sampling_rate=16000)
            window_size = VAD_CONFIG["window_size"]

            current_segment = []
            current_start = None
            current_duration = 0.0
            in_speech = False

            for i in range(0, len(audio_array), window_size):
                chunk = audio_array[i : i + window_size]
                if len(chunk) < window_size:
                    chunk = np.pad(chunk, (0, window_size - len(chunk)))

                speech_dict = vad_iterator(chunk, return_seconds=True)

                if speech_dict:
                    if not in_speech:
                        current_start = i / 16000.0
                        in_speech = True
                    current_segment.extend(chunk)
                elif in_speech:
                    segment_duration = len(current_segment) / 16000.0
                    if segment_duration >= VAD_CONFIG["min_segment_duration"]:
                        yield (
                            current_start,
                            current_start + segment_duration,
                            np.array(current_segment),
                        )
                    current_segment = []
                    in_speech = False
                    current_duration = 0.0

                if in_speech:
                    current_duration = len(current_segment) / 16000.0
                    if current_duration >= max_duration:
                        yield (
                            current_start,
                            current_start + current_duration,
                            np.array(current_segment),
                        )
                        current_segment = []
                        current_start = (i + window_size) / 16000.0
                        current_duration = 0.0

            if current_segment and in_speech:
                segment_duration = len(current_segment) / 16000.0
                if segment_duration >= VAD_CONFIG["min_segment_duration"]:
                    yield (
                        current_start,
                        current_start + segment_duration,
                        np.array(current_segment),
                    )

            vad_iterator.reset_states()

        def batch_segments(segments, max_files=10, max_duration=5.0):
            batch = []
            batch_duration = 0.0

            for start_time, end_time, audio_segment in segments:
                segment_duration = end_time - start_time

                if segment_duration < VAD_CONFIG["silence_padding"]:
                    silence_samples = int(
                        (VAD_CONFIG["silence_padding"] - segment_duration) * 16000
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
            with self.lock:
                with NoStdStreams():
                    outputs = model.transcribe(audio_segments, timestamps=True)
            return outputs

        def emit_results(
            results,
            segments_info,
            progress_queue,
            total_duration,
            processed_duration,
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

                if progress_queue and text:
                    progress_update = {
                        "type": "progress",
                        "chunk_index": batch_index,
                        "total_chunks": total_batches,
                        "partial_text": text,
                        "chunk_words": words,
                    }
                    try:
                        progress_queue.put(progress_update, partition="progress")
                    except Exception as e:
                        print(f"Error putting progress to queue: {e}")

                yield text, words

        def calculate_progress(processed_duration, total_duration):
            if total_duration <= 0:
                return 0.0
            return min(100.0, (processed_duration / total_duration) * 100.0)

        upload_volume.reload()

        file_path = f"/uploads/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_array = load_and_convert_audio(file_path)
        total_duration = len(audio_array) / 16000.0
        processed_duration = 0.0

        all_text_parts = []
        all_words = []

        segments = vad_segment_generator(
            audio_array, VAD_CONFIG["max_segment_duration"]
        )
        batches = batch_segments(
            segments, VAD_CONFIG["batch_max_files"], VAD_CONFIG["batch_max_duration"]
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
                progress_queue,
                total_duration,
                processed_duration,
                batch_index,
                total_batches,
            ):
                if text:
                    all_text_parts.append(text)
                    all_words.extend(words)

            processed_duration += sum(len(seg[2]) / 16000.0 for seg in batch)

        if progress_queue:
            combined_text = " ".join(all_text_parts)
            final_result = {
                "type": "final",
                "text": combined_text,
                "words": all_words,
            }
            try:
                progress_queue.put(final_result, partition="progress")
                progress_queue.put(None, partition="progress")
            except Exception as e:
                print(f"Error putting final result to queue: {e}")

        combined_text = " ".join(all_text_parts)
        return {"text": combined_text, "words": all_words}

    @modal.method()
    def transcribe_batch(
        self,
        filenames: list[str],
        language: str,
    ):
        import os

        import librosa
        import numpy as np

        # Reload volume to see new files
        upload_volume.reload()

        # List files to debug
        files = os.listdir("/uploads")
        print(f"Files in /uploads after reload: {files}")

        results = []
        audio_arrays = []

        # Load all audio files with padding
        for filename in filenames:
            file_path = f"/uploads/{filename}"
            print(f"Looking for batch file: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Batch file not found: {file_path}")

            audio_array, sample_rate = librosa.load(file_path, sr=16000, mono=True)

            # Add 1 second of silence after the audio to help with timestamp computation
            silence_samples = int(sample_rate * 1.0)  # 1 second of silence
            silence = np.zeros(silence_samples, dtype=np.float32)
            padded_audio = np.concatenate([audio_array, silence])

            audio_arrays.append(padded_audio)

        with self.lock:
            with NoStdStreams():
                outputs = self.model.transcribe(audio_arrays, timestamps=True)

        # Process results for each file
        for i, (filename, output) in enumerate(zip(filenames, outputs)):
            text = output.text.strip()
            words = []

            # Extract word timestamps (no adjustment needed since padding is after audio)
            if (
                hasattr(output, "timestamp")
                and output.timestamp
                and "word" in output.timestamp
            ):
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
        Query,
        UploadFile,
        status,
    )
    from fastapi.responses import StreamingResponse
    from fastapi.security import OAuth2PasswordBearer

    transcriber = TranscriberParakeet()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    supported_file_types = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
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
        files: list[UploadFile] = None,
        model: str = Form("parakeet-tdt-0.6b-v2"),
        language: str = Form("en"),
        batch: bool = Form(True),
    ):
        # Handle both single file and multiple files
        upload_files = []
        if file:
            upload_files = [file]
        elif files:
            upload_files = files
        else:
            raise HTTPException(
                status_code=400, detail="Either 'file' or 'files' parameter is required"
            )

        # Upload files to volume
        uploaded_filenames = []
        for upload_file in upload_files:
            audio_suffix = upload_file.filename.split(".")[-1]
            assert audio_suffix in supported_file_types

            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
            file_path = f"/uploads/{unique_filename}"

            print(f"Writing file to: {file_path}")

            # Write file to volume
            with open(file_path, "wb") as f:
                content = upload_file.file.read()
                f.write(content)

            uploaded_filenames.append(unique_filename)

        # Commit the volume to ensure files are persisted
        upload_volume.commit()

        # List files after commit for debugging
        files = os.listdir("/uploads")
        print(f"Files in /uploads after commit: {files}")

        try:
            if batch and len(upload_files) > 1:
                # Use batch transcription
                func = transcriber.transcribe_batch.spawn(
                    filenames=uploaded_filenames,
                    language=language,
                )
                results = func.get()
                return {"results": results}
            else:
                # Single file or forced non-batch
                results = []
                for filename in uploaded_filenames:
                    func = transcriber.transcribe_segment.spawn(
                        filename=filename,
                        language=language,
                    )
                    result = func.get()
                    result["filename"] = filename
                    results.append(result)

                return {"results": results} if len(results) > 1 else results[0]

        finally:
            # Cleanup uploaded files
            for filename in uploaded_filenames:
                try:
                    file_path = f"/uploads/{filename}"
                    print(f"Deleting file: {file_path}")
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")

            # Commit volume changes after cleanup
            upload_volume.commit()

            # List files after cleanup for debugging
            files = os.listdir("/uploads")
            print(f"Files in /uploads after cleanup: {files}")

    @app.post("/v1/audio/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
    def transcribe_from_url(
        audio_file_url: str = Body(...),
        model: str = Body("parakeet-tdt-0.6b-v2"),
        language: str = Body("en"),
        stream: bool = Query(False),
        timestamp_offset: float = Body(0.0),
        batch: bool = Body(True),
    ):
        unique_filename, audio_suffix = download_audio_to_volume(audio_file_url)

        if stream:
            return StreamingResponse(
                stream_transcription_from_file(
                    transcriber, unique_filename, language, timestamp_offset
                ),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
        else:
            try:
                func = transcriber.transcribe_segment_with_offset.spawn(
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

    async def stream_transcription_from_file(
        transcriber, filename: str, language: str, timestamp_offset: float = 0.0
    ):
        import asyncio

        try:
            with modal.Queue.ephemeral() as queue:
                func = transcriber.transcribe_segment_with_offset.spawn(
                    filename=filename,
                    language=language,
                    timestamp_offset=timestamp_offset,
                    progress_queue=queue,
                )

                while True:
                    try:
                        result = await asyncio.wait_for(
                            queue.get.aio(partition="progress"),
                            timeout=30.0,
                        )

                        if result is None:
                            break

                        if result["type"] == "progress":
                            data = {
                                "type": "progress",
                                "chunk_index": result["chunk_index"],
                                "total_chunks": result["total_chunks"],
                                "partial_text": result["partial_text"],
                                "chunk_words": result["chunk_words"],
                            }
                            yield f"data: {json.dumps(data)}\n\n"

                        elif result["type"] == "final":
                            data = {
                                "type": "final",
                                "text": result["text"],
                                "words": result["words"],
                            }
                            yield f"data: {json.dumps(data)}\n\n"
                            break

                    except asyncio.TimeoutError:
                        print(
                            f"Timeout waiting for queue result, checking function status"
                        )
                        try:
                            ret = func.get(timeout=0)
                            print(
                                "Function finished, but no end marker received",
                                type(ret),
                                repr(ret),
                            )
                            error_data = {
                                "type": "error",
                                "message": "Transcription completed but no final result received",
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                            break
                        except TimeoutError:
                            print("Function still running, continuing to wait...")
                            continue
                        except Exception as func_error:
                            print(f"Function failed with error: {func_error}")
                            error_data = {
                                "type": "error",
                                "message": f"Transcription failed: {str(func_error)}",
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                            break

                    except Exception as e:
                        print(f"Error reading from queue: {e}")
                        try:
                            func.get(timeout=0)
                            print("Function completed but queue error occurred")
                            error_data = {
                                "type": "error",
                                "message": f"Queue error: {str(e)}",
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                        except TimeoutError:
                            print(
                                "Function still running despite queue error, breaking"
                            )
                            error_data = {
                                "type": "error",
                                "message": f"Communication error: {str(e)}",
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                        except Exception as func_error:
                            print(f"Function failed: {func_error}")
                            error_data = {
                                "type": "error",
                                "message": f"Transcription failed: {str(func_error)}",
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                        break
        finally:
            try:
                file_path = f"/uploads/{filename}"
                print(f"Deleting file after streaming: {file_path}")
                os.remove(file_path)
                upload_volume.commit()
            except Exception as e:
                print(f"Error cleaning up {filename} after streaming: {e}")

    return app


# Helper class to silence noisy output from NeMo
class NoStdStreams:
    def __init__(self):
        self.devnull = open(os.devnull, "w")

    def __enter__(self):
        self._stdout, self._stderr = sys.stdout, sys.stderr
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout, sys.stderr = self.devnull, self.devnull

    def __exit__(self, exc_type, exc_value, traceback):
        import sys

        sys.stdout, sys.stderr = self._stdout, self._stderr
        self.devnull.close()
