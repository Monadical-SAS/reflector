"""
Shared audio processing constants.

Used by both Hatchet workflows and Celery pipelines for consistent audio encoding.
"""

# Opus codec settings
# ref B0F71CE8-FC59-4AA5-8414-DAFB836DB711
OPUS_STANDARD_SAMPLE_RATE = 48000
# ref B0F71CE8-FC59-4AA5-8414-DAFB836DB711
OPUS_DEFAULT_BIT_RATE = 128000  # 128kbps for good speech quality

# S3 presigned URL expiration
PRESIGNED_URL_EXPIRATION_SECONDS = 7200  # 2 hours

# Waveform visualization
WAVEFORM_SEGMENTS = 255
