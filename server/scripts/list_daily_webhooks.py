#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from reflector.settings import settings


async def list_webhooks():
    """
    List all Daily.co webhooks for this account.
    """
    if not settings.DAILY_API_KEY:
        print("Error: DAILY_API_KEY not set")
        return 1

    headers = {
        "Authorization": f"Bearer {settings.DAILY_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            """
            Daily.co webhook list response format:
            [
              {
                "uuid": "0b4e4c7c-5eaf-46fe-990b-a3752f5684f5",
                "url": "{{webhook_url}}",
                "hmac": "NQrSA5z0FkJ44QPrFerW7uCc5kdNLv3l2FDEKDanL1U=",
                "basicAuth": null,
                "eventTypes": [
                  "recording.started",
                  "recording.ready-to-download"
                ],
                "state": "ACTVIE",
                "failedCount": 0,
                "lastMomentPushed": "2023-08-15T18:29:52.000Z",
                "domainId": "{{domain_id}}",
                "createdAt": "2023-08-15T18:28:30.000Z",
                "updatedAt": "2023-08-15T18:29:52.000Z"
              }
            ]
            """
            resp = await client.get(
                "https://api.daily.co/v1/webhooks",
                headers=headers,
            )
            resp.raise_for_status()
            webhooks = resp.json()

            if not webhooks:
                print("No webhooks found")
                return 0

            print(f"Found {len(webhooks)} webhook(s):\n")

            for webhook in webhooks:
                print("=" * 80)
                print(f"UUID:         {webhook['uuid']}")
                print(f"URL:          {webhook['url']}")
                print(f"State:        {webhook['state']}")
                print(f"Event Types:  {', '.join(webhook.get('eventTypes', []))}")
                print(
                    f"HMAC Secret:  {'✓ Configured' if webhook.get('hmac') else '✗ Not set'}"
                )
                print()

            print("=" * 80)
            print(
                f"\nCurrent DAILY_WEBHOOK_UUID in settings: {settings.DAILY_WEBHOOK_UUID or '(not set)'}"
            )

            return 0

        except httpx.HTTPStatusError as e:
            print(f"Error fetching webhooks: {e}")
            print(f"Response: {e.response.text}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(list_webhooks()))
