# Source: https://docs.daily.co/reference/rest-api/rooms/dialout/start

#

POST

/rooms/:name/dialOut/start

Starts a dialOut with given parameters.

## Path params

`name`

string

The name of the room.

## Body params

`sipUri`

string

sipUri to call. uri should start with `sip:`. Query parameters appended to the sipUri will appear as SIP Headers in the INTIVE message at the remote SIP endpoint. Headers must start with "X-", e.g. to append a header "myexampleHeader" it is appended to sipUri as "sip:<dialout_sip_uri>?X-header-1=val-1&X-header-2=val-2".

`phoneNumber`

string

phone number to call. number must start with country code e.g `+1`

`extension`

string

the extension to dial after dialed number is connected. e.g. `1234`

`waitBeforeExtensionDialSec`

integer

number of seconds to wait before dialing the extension, once dialed number is connected.

Default: 0

`displayName`

string

The sipUri or The phone participant is shown with this name in the web UI.

`userId`

string

userId to assign to the participant. default `userId` is null.

`callerId`

string

determine the phone number used for outbound call (i.e. phone number displayed on the called phone). [purchased phone](/reference/rest-api/phone-numbers/purchased-phone-numbers)

`video`

boolean

Enable SIP video in the room, only available for sipUri.

`codecs`

object

Specify the codecs to use for dial-out.

`audio`

array

Specify the audio codecs to use for dial-out. ['OPUS', 'G722', 'PCMU', 'PCMA']

`video`

array

Specify the video codecs to use for dial-out. ['H264', 'VP8']

## Example requests

**call sip**

**call PSTN**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**400 dialOut already started**

**400 Call closed before command could be delivered**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/rooms/dialout/send-dtmf)
