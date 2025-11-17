# Source: https://docs.daily.co/reference/rest-api/rooms/callTransfer/sip-refer

#

POST

/rooms/:name/sipRefer

[Pay-as-you-go](https://www.daily.co/pricing)

Use SIP REFER to move a SIP attachment on Daily's SIP network to another SIP endpoint (on a different SIP network).

## Path params

`name`

string

The name of the room.

## Example requests

**Default**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**404 invalid sessionId**

**400 Room not in SFU mode**

**400 Call closed before command could be delivered**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/callTransfer/sip-call-transfer)

Next
