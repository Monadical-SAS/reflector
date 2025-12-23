"""
Hatchet workflow constants.
"""

# Rate limit key for LLM API calls (shared across all LLM-calling tasks)
LLM_RATE_LIMIT_KEY = "llm"

# Max LLM calls per second across all tasks
LLM_RATE_LIMIT_PER_SECOND = 10

# Task execution timeouts (seconds)
TIMEOUT_SHORT = 60  # Quick operations: API calls, DB updates
TIMEOUT_MEDIUM = 120  # Single LLM calls, waveform generation
TIMEOUT_LONG = 180  # Action items (larger context LLM)
TIMEOUT_AUDIO = 300  # Audio processing: padding, mixdown
TIMEOUT_HEAVY = 600  # Transcription, fan-out LLM tasks
