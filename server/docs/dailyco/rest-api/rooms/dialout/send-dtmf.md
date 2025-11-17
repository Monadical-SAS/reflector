# Source: https://docs.daily.co/reference/rest-api/rooms/dialout/send-dtmf

#

POST

/rooms/:name/dialOut/sendDTMF

sends DTMF tone.

## Path params

`name`

string

The name of the room.

## Body params

`sessionId`

string

`tones`

string

## Example requests

**Default**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**404 No session running**

**400 Room not in SFU mode**

**400 Call closed before command could be delivered**

Copy to clipboard

;

* * *

[Previous](/reference/rest-api/rooms/dialout/start)

[Next](/reference/rest-api/rooms/dialout/stop)
