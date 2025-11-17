# Source: https://docs.daily.co/reference/rest-api/webhooks/events/streaming-error

# Streaming Error

A streaming error event emits when an error occurred when starting or during a live stream. You might still receive other streaming events, depending on when the error has occurred during the streaming lifecycle.

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

Options: "streaming.error"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`timestamp`

integer

The Unix epoch time in seconds representing when streaming error occurred.

`instance_id`

string

The streaming instance ID.

`error_message`

string

The error message returned.

`room_name`

string

The name of the room where streaming error occurred.

`domain_id`

string

ID of the domain for which streaming error occurred.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/streaming-ended)

[Next](/reference/rest-api/webhooks/events/batch-processor-job-finished)
