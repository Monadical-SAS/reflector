#!/usr/bin/env python3
"""Recreate Daily.co webhook (fixes circuit-breaker FAILED state)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from reflector.settings import settings


async def recreate_webhook(webhook_url: str):
    """Delete all webhooks and create new one."""
    if not settings.DAILY_API_KEY:
        print("Error: DAILY_API_KEY not set")
        return 1

    headers = {
        "Authorization": f"Bearer {settings.DAILY_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        # List existing webhooks
        resp = await client.get("https://api.daily.co/v1/webhooks", headers=headers)
        resp.raise_for_status()
        webhooks = resp.json()

        # Delete all existing webhooks
        for wh in webhooks:
            uuid = wh["uuid"]
            print(f"Deleting webhook {uuid} (state: {wh['state']})")
            await client.delete(
                f"https://api.daily.co/v1/webhooks/{uuid}", headers=headers
            )

        # Create new webhook
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

        resp = await client.post(
            "https://api.daily.co/v1/webhooks", headers=headers, json=webhook_data
        )
        resp.raise_for_status()
        result = resp.json()

        print(f"Created webhook {result['uuid']} (state: {result['state']})")
        print(f"URL: {result['url']}")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recreate_daily_webhook.py <webhook_url>")
        print(
            "Example: python recreate_daily_webhook.py https://example.com/v1/daily/webhook"
        )
        sys.exit(1)

    sys.exit(asyncio.run(recreate_webhook(sys.argv[1])))
