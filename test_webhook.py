#!/usr/bin/env python3
"""Test webhook functionality."""

import asyncio
import json
from datetime import datetime, timezone

import httpx
from reflector.db import get_database
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import transcripts_controller, SourceKind
from reflector.worker.webhook import send_transcript_webhook, test_webhook


async def main():
    # Connect to database
    db = get_database()
    await db.connect()
    
    try:
        # Get first room with webhook configured (for testing)
        rooms = await rooms_controller.get_all()
        test_room = None
        
        for room in rooms:
            if room.webhook_url:
                test_room = room
                break
        
        if not test_room:
            print("No rooms with webhook configured. Creating test room...")
            test_room = await rooms_controller.add(
                name="webhook-test-room",
                user_id="test-user",
                zulip_auto_post=False,
                zulip_stream="",
                zulip_topic="",
                is_locked=False,
                room_mode="normal",
                recording_type="cloud",
                recording_trigger="automatic-2nd-participant",
                is_shared=False,
                webhook_url="https://webhook.site/unique-id",  # Replace with your webhook.site URL
                webhook_secret="test-secret-123",
            )
            print(f"Created test room: {test_room.name}")
        
        print(f"\nTesting webhook for room: {test_room.name}")
        print(f"Webhook URL: {test_room.webhook_url}")
        print(f"Webhook Secret: {test_room.webhook_secret[:10]}..." if test_room.webhook_secret else "No secret")
        
        # Test webhook endpoint
        print("\n1. Testing webhook endpoint...")
        result = await test_webhook(test_room.id)
        print(f"Test result: {json.dumps(result, indent=2)}")
        
        # Find a transcript for this room
        transcripts = await transcripts_controller.get_all(
            room_id=test_room.id,
            limit=1
        )
        
        if transcripts:
            transcript = transcripts[0]
            print(f"\n2. Found transcript: {transcript.id}")
            print(f"   Title: {transcript.title}")
            print(f"   Duration: {transcript.duration}s")
            
            # Test sending actual webhook
            print("\n3. Testing actual webhook send (this would normally be async via Celery)...")
            try:
                # Call the webhook task directly for testing
                from reflector.worker.webhook import send_transcript_webhook
                
                # We'll call the inner async function directly for testing
                task = send_transcript_webhook.s(transcript.id, test_room.id)
                print("Webhook task created. In production, this would be executed by Celery.")
                
                # For immediate testing, let's call the inner function
                print("\n4. Calling webhook directly for testing...")
                await send_transcript_webhook.__wrapped__.__wrapped__(
                    None,  # self parameter (mock)
                    transcript.id,
                    test_room.id
                )
                print("✅ Webhook sent successfully!")
                
            except Exception as e:
                print(f"❌ Error sending webhook: {e}")
        else:
            print(f"\nNo transcripts found for room {test_room.id}")
            print("Create a transcript first by recording in this room.")
        
    finally:
        await db.disconnect()


if __name__ == "__main__":
    print("Webhook Test Script")
    print("=" * 50)
    asyncio.run(main())