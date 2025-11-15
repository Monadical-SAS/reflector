#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reflector.dailyco_api import (
    CreateWebhookRequest,
    DailyApiClient,
)
from reflector.settings import settings


async def setup_webhook(webhook_url: str):
    """
    Create or update Daily.co webhook for this environment using dailyco_api module.
    Uses DAILY_WEBHOOK_UUID to identify existing webhook.
    """
    if not settings.DAILY_API_KEY:
        print("Error: DAILY_API_KEY not set")
        return 1

    if not settings.DAILY_WEBHOOK_SECRET:
        print("Error: DAILY_WEBHOOK_SECRET not set")
        return 1

    event_types = [
        "participant.joined",
        "participant.left",
        "recording.started",
        "recording.ready-to-download",
        "recording.error",
    ]

    async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
        webhook_uuid = settings.DAILY_WEBHOOK_UUID

        if webhook_uuid:
            print(f"Updating existing webhook {webhook_uuid}...")
            try:
                # Note: Daily.co doesn't support PATCH well, so we delete + recreate
                await client.delete_webhook(webhook_uuid)
                print(f"Deleted old webhook {webhook_uuid}")

                request = CreateWebhookRequest(
                    url=webhook_url,
                    eventTypes=event_types,
                    hmac=settings.DAILY_WEBHOOK_SECRET,
                )
                result = await client.create_webhook(request)

                print(
                    f"✓ Created replacement webhook {result.uuid} (state: {result.state})"
                )
                print(f"  URL: {result.url}")

                webhook_uuid = result.uuid

            except Exception as e:
                if hasattr(e, "response") and e.response.status_code == 404:
                    print(f"Webhook {webhook_uuid} not found, creating new one...")
                    webhook_uuid = None  # Fall through to creation
                else:
                    print(f"Error updating webhook: {e}")
                    return 1

        if not webhook_uuid:
            print("Creating new webhook...")
            request = CreateWebhookRequest(
                url=webhook_url,
                eventTypes=event_types,
                hmac=settings.DAILY_WEBHOOK_SECRET,
            )
            result = await client.create_webhook(request)
            webhook_uuid = result.uuid

            print(f"✓ Created webhook {webhook_uuid} (state: {result.state})")
            print(f"  URL: {result.url}")
            print()
            print("=" * 60)
            print("IMPORTANT: Add this to your environment variables:")
            print("=" * 60)
            print(f"DAILY_WEBHOOK_UUID: {webhook_uuid}")
            print("=" * 60)
            print()

            # Try to write UUID to .env file
            env_file = Path(__file__).parent.parent / ".env"
            if env_file.exists():
                lines = env_file.read_text().splitlines()
                updated = False

                # Update existing DAILY_WEBHOOK_UUID line or add it
                for i, line in enumerate(lines):
                    if line.startswith("DAILY_WEBHOOK_UUID="):
                        lines[i] = f"DAILY_WEBHOOK_UUID={webhook_uuid}"
                        updated = True
                        break

                if not updated:
                    lines.append(f"DAILY_WEBHOOK_UUID={webhook_uuid}")

                env_file.write_text("\n".join(lines) + "\n")
                print(f"✓ Also saved to local .env file")
            else:
                print(f"⚠ Local .env file not found - please add manually")

            return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recreate_daily_webhook.py <webhook_url>")
        print(
            "Example: python recreate_daily_webhook.py https://example.com/v1/daily/webhook"
        )
        print()
        print("Behavior:")
        print("  - If DAILY_WEBHOOK_UUID set: Deletes old webhook, creates new one")
        print(
            "  - If DAILY_WEBHOOK_UUID empty: Creates new webhook, saves UUID to .env"
        )
        sys.exit(1)

    sys.exit(asyncio.run(setup_webhook(sys.argv[1])))
