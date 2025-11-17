# Source: https://docs.daily.co/reference/rest-api/dialin/pinless-call-update

#

POST

/dialin/pinlessCallUpdate

[Pay-as-you-go](https://www.daily.co/pricing)

Direct a SIP or PSTN call on hold to a specified SIP URI associated to a Daily Room.

## Body params

`callId`

string

CallId is represented by UUID and represents the sessionId in the SIP Network. This is obtained from the [webhook payload](/guides/products/dial-in-dial-out/dialin-pinless#incoming-call-triggers-the-webhook).

`callDomain`

string

Call Domain is represented by UUID and represents your Daily Domain on the SIP Network. This is obtained from the [webhook payload](/guides/products/dial-in-dial-out/dialin-pinless#incoming-call-triggers-the-webhook).

`sipUri`

string

This SIP URI is associated to the Daily Room that you want to forward the SIP Interconnect call to.

## Example requests

**Default**

Copy to clipboard

## Example responses

**200 OK**

**400 Missing fields**

**404 Call Forwarding Failed**

Copy to clipboard
