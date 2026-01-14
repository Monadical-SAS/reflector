"""
Daily.co recording instanceId generation utilities.

Deterministic instance ID generation for cloud and raw-tracks recordings.
MUST match frontend logic
"""

from uuid import UUID, uuid5

from reflector.utils.string import NonEmptyString

# Namespace UUID for UUIDv5 generation of raw-tracks instanceIds
# DO NOT CHANGE: Breaks instanceId determinism across deployments and frontend/backend matching
RAW_TRACKS_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def generate_cloud_instance_id(meeting_id: NonEmptyString) -> UUID:
    """
    Generate instanceId for cloud recording.

    Cloud recordings use meeting ID directly as instanceId.
    This ensures each meeting has one unique cloud recording.
    """
    return UUID(meeting_id)


def generate_raw_tracks_instance_id(meeting_id: NonEmptyString) -> UUID:
    """
    Generate instanceId for raw-tracks recording.

    Raw-tracks recordings use UUIDv5(meeting_id, namespace) to ensure
    different instanceId from cloud while remaining deterministic.

    Daily.co requires cloud and raw-tracks to have different instanceIds
    for concurrent recording.
    """
    return uuid5(RAW_TRACKS_NAMESPACE, meeting_id)
