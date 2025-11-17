# Source: https://docs.daily.co/reference/rest-api/webhooks/events/dialout-error

# Dialout error

Emitted when the dial-out session encounters an error when connecting to a call.

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

Options: "dialout.error"

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

The sessionId of the dial-out session.

`user_id`

string

The userId of the dial-out session (if supplied during the API call).

`domain_id`

string

ID of the domain for which dial-out has error.

`room`

string

The name of the room where dial-out has error.

`error_msg`

string

message describing the error

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/dialout-stopped)

[Next](/reference/rest-api/webhooks/events/dialout-warning)
