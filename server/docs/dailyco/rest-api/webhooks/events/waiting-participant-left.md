# Source: https://docs.daily.co/reference/rest-api/webhooks/events/waiting-participant-left

# Waiting Participant Left

A waiting participant left event is sent when a knocking participant (see [blog post](https://www.daily.co/blog/manage-call-permissions-with-dailys-knocking-feature/)) leaves the knocking state. In other words, when a knocker begins to knock and leaves before being allowed into a room, a `waiting-participant.left` event is sent. If a knocker is allowed into a room and then leaves, a [`participant.left`](./participant-left) event is sent.

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

Options: "waiting-participant.left"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`joined_at`

number

The Unix epoch time in seconds representing when the waiting participant joined.

`duration`

number

The time in seconds representing how long the participant was in the call.

`session_id`

string

The user session ID, or participant id.

`room`

string

The name of the room.

`user_id`

string

The ID of the user, set by the meeting token.

`user_name`

string

The name of the user, set by the meeting token.

`owner`

boolean

A flag determining if this user is considered the owner.

`networkQualityState`

string

The quality of the user's network.

Options: "unknown","good","warning","bad"

`will_eject_at`

integer

The Unix epoch time in seconds representing when the participant will be ejected.

`permissions`

object

The permissions object, that describes what the participant is permitted to do during this call.

`hasPresence`

boolean

Determines whether the participant is "present" or "hidden"

`canSend`

array

Array of strings identifying which types of media the participant can send or a boolean to grant/revoke permissions for all media types.

`canReceive`

object

Which media the participant should be permitted to receive.

[See here for `canReceive` object format](/reference/daily-js/instance-methods/participants#permissionscanreceive-properties).

`canAdmin`

array

Array of strings identifying which types of admin tasks the participant can do or a boolean to grant/revoke permissions for all types.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/waiting-participant-joined)

[Next](/reference/rest-api/webhooks/events/recording-started)
