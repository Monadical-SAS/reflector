# Source: https://docs.daily.co/reference/rest-api/rooms/transcription/stop

#

POST

/rooms/:name/transcription/stop

Stops a transcription.

## Path params

`name`

string

The name of the room.

## Body params

`instanceId`

string

## Example requests

**Default**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**404 No transcription to stop**

**400 Stream in progress**

**400 Room not in SFU mode**

**400 Call closed before command could be delivered**

**400 Deepgram API key invalid**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/transcription/update)

Next
