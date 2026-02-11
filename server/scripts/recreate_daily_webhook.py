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
    Create Daily.co webhook. Deletes any existing webhooks first, then creates the new one.
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
        webhooks = await client.list_webhooks()
        for wh in webhooks:
            await client.delete_webhook(wh.uuid)
            print(f"Deleted webhook {wh.uuid}")

        request = CreateWebhookRequest(
            url=webhook_url,
            eventTypes=event_types,
            hmac=settings.DAILY_WEBHOOK_SECRET,
        )
        result = await client.create_webhook(request)
        webhook_uuid = result.uuid

        print(f"✓ Created webhook {webhook_uuid} (state: {result.state})")
        print(f"  URL: {result.url}")

        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            lines = env_file.read_text().splitlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("DAILY_WEBHOOK_UUID="):
                    lines[i] = f"DAILY_WEBHOOK_UUID={webhook_uuid}"
                    updated = True
                    break
            if not updated:
                lines.append(f"DAILY_WEBHOOK_UUID={webhook_uuid}")
            env_file.write_text("\n".join(lines) + "\n")
            print("✓ Saved DAILY_WEBHOOK_UUID to .env")

        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recreate_daily_webhook.py <webhook_url>")
        print(
            "Example: python recreate_daily_webhook.py https://example.com/v1/daily/webhook"
        )
        print()
        print("Deletes all existing webhooks, then creates a new one.")
        sys.exit(1)

    sys.exit(asyncio.run(setup_webhook(sys.argv[1])))
