#!/usr/bin/env python3
"""Test script to fetch Daily.co recordings for a specific room and show raw API response."""

import asyncio
import json

from reflector.video_platforms.factory import create_platform_client


async def main():
    room_name = "daily-private-igor-20260110042117"

    print(f"\n=== Fetching recordings for room: {room_name} ===\n")

    async with create_platform_client("daily") as client:
        recordings = await client.list_recordings(room_name=room_name)

    print(f"Found {len(recordings)} recording objects from Daily.co API\n")

    for i, rec in enumerate(recordings, 1):
        print(f"--- Recording #{i} ---")
        print(f"ID: {rec.id}")
        print(f"Room: {rec.room_name}")
        print(f"Start TS: {rec.start_ts}")
        print(f"Status: {rec.status}")
        print(f"Duration: {rec.duration}")
        print(f"Type: {rec.type}")
        print(f"Tracks count: {len(rec.tracks)}")

        if rec.tracks:
            print(f"Tracks:")
            for j, track in enumerate(rec.tracks, 1):
                print(f"  Track {j}: {track.s3Key}")

        print(f"\nRaw JSON:\n{json.dumps(rec.model_dump(), indent=2, default=str)}\n")


if __name__ == "__main__":
    asyncio.run(main())
