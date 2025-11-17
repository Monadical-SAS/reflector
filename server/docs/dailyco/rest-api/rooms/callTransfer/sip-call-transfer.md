# Source: https://docs.daily.co/reference/rest-api/rooms/callTransfer/sip-call-transfer

#

POST

/rooms/:name/sipCallTransfer

[Pay-as-you-go](https://www.daily.co/pricing)

Transfer call to another SIP endpoint. This SIP endpoint can be associated to another Daily Room or outside Daily.

## Path params

`name`

string

The name of the room.

## Body params

`sessionId`

string

`toEndPoint`

string

the SIP/phoneNumber endpoint to transfer the call to.

`callerId`

string

determine the phone number used for outbound call (i.e. phone number displayed on the called phone). [purchased phone](/reference/rest-api/phone-numbers/purchased-phone-numbers)

`waitBeforeExtensionDialSec`

integer

number of seconds to wait before dialing the extension, once dialed number is connected.

Default: 0

`extension`

string

the extension to dial after dialed number is connected. e.g. `1234`

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

Previous

[Next](/reference/rest-api/rooms/callTransfer/sip-refer)
