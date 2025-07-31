"""
@vibe-generated
File size validation for audio downloads
"""
from typing import Optional

from reflector.logger import logger
from reflector.settings import settings



MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE = getattr(settings, "MAX_AUDIO_FILE_SIZE", MAX_FILE_SIZE_MB * 1024 * 1024)




async def check_file_size(url: str, session) -> tuple[bool, Optional[str]]:
    """
    Check file size via HEAD request.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            # Check Content-Length header
            content_length = response.headers.get('Content-Length')
            if content_length:
                size = int(content_length)
                if size > MAX_FILE_SIZE:
                    size_mb = size / (1024 * 1024)
                    max_mb = MAX_FILE_SIZE / (1024 * 1024)
                    return False, f"File too large: {size_mb:.1f}MB exceeds maximum of {max_mb:.1f}MB"
            
            # Check Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if content_type:
                # Allow audio/* and video/* types
                if not (content_type.startswith('audio/') or 
                        content_type.startswith('video/') or
                        content_type == 'application/octet-stream'):
                    return False, f"Invalid content type: {content_type}"
            
            return True, None
            
    except Exception as e:
        # If HEAD fails, we'll still allow the download but log the warning
        logger.warning(f"Failed to check file size for {url}: {e}")
        return True, None