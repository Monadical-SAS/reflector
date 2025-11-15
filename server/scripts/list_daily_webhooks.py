#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reflector.dailyco_api import DailyApiClient
from reflector.settings import settings


async def list_webhooks():
    """List all Daily.co webhooks for this account using dailyco_api module."""
    if not settings.DAILY_API_KEY:
        print("Error: DAILY_API_KEY not set")
        return 1

    async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
        try:
            webhooks = await client.list_webhooks()

            if not webhooks:
                print("No webhooks found")
                return 0

            print(f"Found {len(webhooks)} webhook(s):\n")

            for webhook in webhooks:
                print("=" * 80)
                print(f"UUID:         {webhook.uuid}")
                print(f"URL:          {webhook.url}")
                print(f"State:        {webhook.state}")
                print(f"Event Types:  {', '.join(webhook.eventTypes)}")
                print(
                    f"HMAC Secret:  {'✓ Configured' if webhook.hmac else '✗ Not set'}"
                )
                print()

            print("=" * 80)
            print(
                f"\nCurrent DAILY_WEBHOOK_UUID in settings: {settings.DAILY_WEBHOOK_UUID or '(not set)'}"
            )

            return 0

        except Exception as e:
            print(f"Error fetching webhooks: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(list_webhooks()))
