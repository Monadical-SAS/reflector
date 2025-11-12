#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from reflector.settings import settings


async def setup_webhook(webhook_url: str):
    """
    Create or update Daily.co webhook for this environment.
    Uses DAILY_WEBHOOK_UUID to identify existing webhook.
    """
    if not settings.DAILY_API_KEY:
        print("Error: DAILY_API_KEY not set")
        return 1

    headers = {
        "Authorization": f"Bearer {settings.DAILY_API_KEY}",
        "Content-Type": "application/json",
    }

    webhook_data = {
        "url": webhook_url,
        "eventTypes": [
            "participant.joined",
            "participant.left",
            "recording.started",
            "recording.ready-to-download",
            "recording.error",
        ],
        "hmac": settings.DAILY_WEBHOOK_SECRET,
    }

    async with httpx.AsyncClient() as client:
        webhook_uuid = settings.DAILY_WEBHOOK_UUID

        if webhook_uuid:
            # Update existing webhook
            print(f"Updating existing webhook {webhook_uuid}...")
            try:
                resp = await client.patch(
                    f"https://api.daily.co/v1/webhooks/{webhook_uuid}",
                    headers=headers,
                    json=webhook_data,
                )
                resp.raise_for_status()
                result = resp.json()
                print(f"✓ Updated webhook {result['uuid']} (state: {result['state']})")
                print(f"  URL: {result['url']}")
                return 0
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    print(f"Webhook {webhook_uuid} not found, creating new one...")
                    webhook_uuid = None  # Fall through to creation
                else:
                    print(f"Error updating webhook: {e}")
                    return 1

        if not webhook_uuid:
            # Create new webhook
            print("Creating new webhook...")
            resp = await client.post(
                "https://api.daily.co/v1/webhooks", headers=headers, json=webhook_data
            )
            resp.raise_for_status()
            result = resp.json()
            webhook_uuid = result["uuid"]

            print(f"✓ Created webhook {webhook_uuid} (state: {result['state']})")
            print(f"  URL: {result['url']}")

            # Write UUID to .env file
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
                print(f"✓ Saved webhook UUID to .env")
            else:
                print(f"⚠ .env file not found at {env_file}")
                print(f"  Add to .env manually: DAILY_WEBHOOK_UUID={webhook_uuid}")

            return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recreate_daily_webhook.py <webhook_url>")
        print(
            "Example: python recreate_daily_webhook.py https://example.com/v1/daily/webhook"
        )
        print()
        print("Behavior:")
        print("  - If DAILY_WEBHOOK_UUID set: Updates existing webhook")
        print(
            "  - If DAILY_WEBHOOK_UUID empty: Creates new webhook, saves UUID to .env"
        )
        sys.exit(1)

    sys.exit(asyncio.run(setup_webhook(sys.argv[1])))
