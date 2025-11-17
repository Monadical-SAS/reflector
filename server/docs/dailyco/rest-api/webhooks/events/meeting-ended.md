# Source: https://docs.daily.co/reference/rest-api/webhooks/events/meeting-ended

# Meeting Ended

A meeting ended event is emitted when the last participant in a call leaves. There can be a delay up to 20 seconds to determine if the meeting has ended, permitting reconnections, before sending the event.

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

Options: "meeting.ended"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`start_ts`

number

The Unix epoch time in seconds representing when the meeting started.

`end_ts`

number

The Unix epoch time in seconds representing when the meeting ended.

`meeting_id`

string

The meeting ID.

`room`

string

The name of the room.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/meeting-started)

[Next](/reference/rest-api/webhooks/events/participant-joined)
