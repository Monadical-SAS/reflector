# Source: https://docs.daily.co/reference/rest-api/webhooks/events/dialin-connected

# DialIn connected

Emitted when the session when the remote end calls (via SIP or PSTN) and the connection is established with Daily's Room. If a user is present in the Daily Room, the call will be directly connected and voice should flow between the PSTN phone number and the Daily Room.

## Webhook Events

There are five common fields all events share:

`version`

string

Represents the version of the event. This uses [semantic versioning](https://semver.org/) to inform a consumer if the payload has introduced any breaking changes.

`type`

string

Represents the type of the event described in the payload.

`id`

string

An identifier representing this specific event.

`payload`

object

An object representing the event, whose fields are described below.

`event_ts`

number

Documenting when the webhook itself was sent. This timestamp is different than the time of the event the webhook describes. For example, a recording.started event will contain a start_ts timestamp of when the actual recording started, and a slightly later event_ts timestamp indicating when the webhook event was sent.

## Payload

`version`

string

The semantic version of the current message.

`type`

string

The type of event that is being provided.

Options: "dialin.connected"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`timestamp`

integer

The Unix epoch time in seconds representing when this event occurred.

`session_id`

string

The sessionId of the dial-in session.

`sip_from`

string

sip address of the incoming call.

`domain_id`

string

ID of the domain corresponding to this dial-in event.

`room`

string

The name of the room where dial-in event occurred.

`display_name`

string

name displayed for the incoming user.

`sip_headers`

object

sip header and header values in the incoming sip invite.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/dialin-ready)

[Next](/reference/rest-api/webhooks/events/dialin-stopped)
