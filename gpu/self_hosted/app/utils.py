import logging
import os
import sys
import uuid
from contextlib import contextmanager
from typing import Mapping
from urllib.parse import urlparse
from pathlib import Path

import requests
from fastapi import HTTPException

from .config import SUPPORTED_FILE_EXTENSIONS, UPLOADS_PATH

logger = logging.getLogger(__name__)


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


def ensure_dirs():
    UPLOADS_PATH.mkdir(parents=True, exist_ok=True)


def detect_audio_format(url: str, headers: Mapping[str, str]) -> str:
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


def download_audio_to_uploads(audio_file_url: str) -> tuple[Path, str]:
    response = requests.head(audio_file_url, allow_redirects=True)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found")

    response = requests.get(audio_file_url, allow_redirects=True)
    response.raise_for_status()

    audio_suffix = detect_audio_format(audio_file_url, response.headers)
    unique_filename = f"{uuid.uuid4()}.{audio_suffix}"
    file_path: Path = UPLOADS_PATH / unique_filename

    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path, audio_suffix


@contextmanager
def download_audio_file(audio_file_url: str):
    """Download an audio file to UPLOADS_PATH and remove it after use.

    Yields (file_path: Path, audio_suffix: str).
    """
    file_path, audio_suffix = download_audio_to_uploads(audio_file_url)
    try:
        yield file_path, audio_suffix
    finally:
        try:
            file_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Error deleting temporary file %s: %s", file_path, e)


@contextmanager
def cleanup_uploaded_files(file_paths: list[Path]):
    """Ensure provided file paths are removed after use.

    The provided list can be populated inside the context; all present entries
    at exit will be deleted.
    """
    try:
        yield file_paths
    finally:
        for path in list(file_paths):
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                logger.error("Error deleting temporary file %s: %s", path, e)
