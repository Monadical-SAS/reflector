# Source: https://docs.daily.co/reference/rest-api/rooms/transcription/update

#

POST

/rooms/:name/transcription/update

Update a transcription instance.

## Path params

`name`

string

The name of the room.

## Body params

`instanceId`

string

instanceId to be updated.

`participants`

array

A list of participant IDs to be transcribed. Only the participant IDs included in this array will be processed

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

[Previous](/reference/rest-api/rooms/transcription/start)

[Next](/reference/rest-api/rooms/transcription/stop)
