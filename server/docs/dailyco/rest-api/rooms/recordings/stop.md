# Source: https://docs.daily.co/reference/rest-api/rooms/recordings/stop

#

POST

/rooms/:name/recordings/stop

[Pay-as-you-go](https://www.daily.co/pricing)

Stops a recording. Returns a `400` HTTP status code if no recording is active.

If multiple streaming instances are running, each instance must be stopped individually by a call to this endpoint with the instance's unique `instanceId`. If a `"raw-tracks"` recording is being used, a `type` must be declared of value `"raw-tracks"`.

## Path params

`name`

string

The name of the room.

## Body params

`instanceId`

string

UUID for a streaming or recording session. Used when multiple streaming or recording sessions are running for single room.

`type`

string

The type of recording you are attempting to stop.

Options: "cloud","raw-tracks"

Default: cloud

## Example requests

**Request**

**With Instance Id**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/recordings/update)

Next
