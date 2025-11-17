# Source: https://docs.daily.co/reference/rest-api/rooms/live-streaming/stop

#

POST

/rooms/:name/live-streaming/stop

Stops a live stream in a given room.

If multiple RTMP endpoints are being live streamed, calling this endpoint will stop all live streams.

If multiple streaming instances are running, each instance must be stopped individually by a call to this endpoint with the instance's unique `instanceId`.

## Path params

`name`

string

The name of the room.

## Body params

`instanceId`

string

UUID for a streaming or recording session. Used when multiple streaming or recording sessions are running for single room.

## Example requests

**Request**

**With Instance Id**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/live-streaming/update)

Next
