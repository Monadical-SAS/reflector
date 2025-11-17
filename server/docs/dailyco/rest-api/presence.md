# Source: https://docs.daily.co/reference/rest-api/presence

# Presence

This endpoint provides near-real-time participant presence data[0].

`/presence` accepts no options and quickly returns all active participants the requestor can see, grouped by room.

**`/presence` vs `/meetings` vs `/logs`**

Please use this endpoint (not `/meetings`) if you need to know the current state of rooms and participants. If you need more in-depth analytics please see [Meeting Analytics](/reference/rest-api/meetings) or [Logs](/reference/rest-api/logs).

## The "presence" object

Copy to clipboard

## Example request

Copy to clipboard

**Note** : It should be sufficient to query this endpoint no more frequently than once every 15 seconds to get a complete picture of all of the participants on your domain.

[0] delay of up to 15 seconds.
