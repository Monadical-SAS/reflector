# Source: https://docs.daily.co/reference/rest-api/rooms/dialout/stop

#

POST

/rooms/:name/dialOut/stop

Stops a dialOut.

## Path params

`name`

string

The name of the room.

## Body params

`sessionId`

string

## Example requests

**Default**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**404 No dialout to stop**

**400 Room not in SFU mode**

**400 Call closed before command could be delivered**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/dialout/send-dtmf)

Next
