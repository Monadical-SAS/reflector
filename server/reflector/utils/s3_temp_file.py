"""
S3 Temporary File Context Manager

Provides automatic cleanup of S3 files with retry logic and proper error handling.
"""

from typing import Optional
from reflector.storage.base import Storage
from reflector.logger import logger
from reflector.utils.retry import retry


class S3TemporaryFile:
    """
    Async context manager for temporary S3 files with automatic cleanup.

    Ensures that uploaded files are deleted even if exceptions occur during processing.
    Uses retry logic for all S3 operations to handle transient failures.

    Example:
        async with S3TemporaryFile(storage, "temp/audio.wav") as s3_file:
            url = await s3_file.upload(audio_data)
            # Use url for processing
        # File is automatically cleaned up here
    """

    def __init__(self, storage: Storage, filepath: str):
        """
        Initialize the temporary file context.

        Args:
            storage: Storage instance for S3 operations
            filepath: S3 key/path for the temporary file
        """
        self.storage = storage
        self.filepath = filepath
        self.uploaded = False
        self._url: Optional[str] = None

    async def __aenter__(self):
        """Enter the context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and clean up the file.

        Cleanup is attempted even if an exception occurred during processing.
        Cleanup failures are logged but don't raise exceptions.
        """
        if self.uploaded:
            try:
                await self._delete_with_retry()
                logger.info(f"Successfully cleaned up S3 file: {self.filepath}")
            except Exception as e:
                # Log the error but don't raise - we don't want cleanup failures
                # to mask the original exception
                logger.warning(
                    f"Failed to cleanup S3 file {self.filepath} after retries: {e}"
                )
        return False  # Don't suppress exceptions

    async def upload(self, data: bytes) -> str:
        """
        Upload data to S3 and return the public URL.

        Args:
            data: File data to upload

        Returns:
            Public URL for the uploaded file

        Raises:
            Exception: If upload or URL generation fails after retries
        """
        await self._upload_with_retry(data)
        self.uploaded = True
        self._url = await self._get_url_with_retry()
        return self._url

    @property
    def url(self) -> Optional[str]:
        """Get the URL of the uploaded file, if available."""
        return self._url

    async def _upload_with_retry(self, data: bytes):
        """Upload file to S3 with retry logic."""

        async def upload():
            await self.storage.put_file(self.filepath, data)
            logger.debug(f"Successfully uploaded file to S3: {self.filepath}")
            return True  # Return something to indicate success

        await retry(upload)(
            retry_attempts=3,
            retry_timeout=30.0,
            retry_backoff_interval=0.5,
            retry_backoff_max=5.0,
        )

    async def _get_url_with_retry(self) -> str:
        """Get public URL for the file with retry logic."""

        async def get_url():
            url = await self.storage.get_file_url(self.filepath)
            logger.debug(f"Generated public URL for S3 file: {self.filepath}")
            return url

        return await retry(get_url)(
            retry_attempts=3,
            retry_timeout=30.0,
            retry_backoff_interval=0.5,
            retry_backoff_max=5.0,
        )

    async def _delete_with_retry(self):
        """Delete file from S3 with retry logic."""

        async def delete():
            await self.storage.delete_file(self.filepath)
            logger.debug(f"Successfully deleted S3 file: {self.filepath}")
            return True  # Return something to indicate success

        await retry(delete)(
            retry_attempts=3,
            retry_timeout=30.0,
            retry_backoff_interval=0.5,
            retry_backoff_max=5.0,
        )


# Convenience function for simpler usage
async def temporary_s3_file(storage: Storage, filepath: str):
    """
    Create a temporary S3 file context manager.

    This is a convenience wrapper around S3TemporaryFile for simpler usage.

    Args:
        storage: Storage instance for S3 operations
        filepath: S3 key/path for the temporary file

    Example:
        async with temporary_s3_file(storage, "temp/audio.wav") as s3_file:
            url = await s3_file.upload(audio_data)
            # Use url for processing
    """
    return S3TemporaryFile(storage, filepath)
