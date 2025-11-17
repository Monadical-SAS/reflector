# Source: https://docs.daily.co/reference/rest-api/webhooks/events/recording-error

# Recording Error

If an error occurs during recording, or before a recording can be started, a `recording.error` event may be emitted. You may still receive a `recording.started` event, or ` recording.ready-to-download` event, depending on when the error was emitted during the recording lifecycle.

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

Options: "recording.error"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`action`

string

A string describing the event that was emitted.

Options: "clourd-recording-err"

`error_msg`

string

The error message returned.

`instance_id`

string

The recording instance ID that was passed into the start recording command.

`room_name`

string

The name of the room where the recording was made.

`timestamp`

integer

The Unix epoch time in seconds representing when the error was emitted.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/recording-ready-to-download)

[Next](/reference/rest-api/webhooks/events/transcript-started)
