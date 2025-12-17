"""
Hatchet workflow utilities.

Shared helpers for Hatchet task implementations.
"""


def to_dict(output) -> dict:
    """Convert task output to dict, handling both dict and Pydantic model returns.

    Hatchet SDK can return task outputs as either raw dicts or Pydantic models
    depending on serialization context. This normalizes the output for consistent
    downstream processing.
    """
    if isinstance(output, dict):
        return output
    return output.model_dump()
