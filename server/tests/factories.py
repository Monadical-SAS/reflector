from uuid import uuid4
from datetime import datetime


def make_transcript(**kwargs):
    """Simple factory for test transcript data.
    
    Usage:
        transcript = make_transcript()
        transcript = make_transcript(title="Custom Title")
        transcript = make_transcript(
            title="Meeting",
            topics=[{"transcript": "Discussion text"}]
        )
    """
    defaults = {
        "id": str(uuid4()),
        "title": "Test Transcript",
        "status": "complete",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "topics": [],
        "short_summary": None,
        "long_summary": None,
    }
    
    # Merge defaults with provided kwargs
    return {**defaults, **kwargs}