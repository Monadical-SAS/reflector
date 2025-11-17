# Source: https://docs.daily.co/reference/rest-api/webhooks/events/transcript-started

# Transcript Started

A transcript started event emits when Daily begins to transcribe a call. These can be activated via [`startTranscription()`](/reference/daily-js/instance-methods/start-transcription), via the [REST API](/reference/rest-api/rooms/transcription/start), or within [Prebuilt](/guides/products/prebuilt).

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

Documenting when the webhook itself was sent. This timestamp is different than the time of the event the webhook describes. For example, a transcript.started event will contain a start_ts timestamp of when the actual transcript started, and a slightly later event_ts timestamp indicating when the webhook event was sent.

## Payload

`version`

string

The semantic version of the current message.

`type`

string

The type of event that is being provided.

Options: "transcript.started"

`id`

string

The unique identifier for this webhook event.

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`id`

string

The unique identifier for the transcription event.

`info`

object

Additional information related to the transcription event.

`instanceId`

string

The instance ID related to the event.

`room_id`

string

The ID of the room where the event occurred.

`mtg_session_id`

string

The meeting session ID related to the event.

`max_participants`

integer

The maximum number of participants allowed in the transcription session.

`duration`

integer

The duration of the session in seconds.

`participant_minutes`

integer

The cumulative participant minutes for the transcription session.

`status`

string

The current status of the transcription event.

Options: "t_in_progress","t_completed","t_failed"

`out_params`

object

The output parameters of the transcription event.

`s3`

object

Details for the S3 storage of the transcription output.

`key`

string

The S3 key for the transcription output file.

`bucket`

string

The S3 bucket where the transcription output is stored.

`region`

string

The AWS region of the S3 bucket.

Copy to clipboard

;

* * *

[Previous](/reference/rest-api/webhooks/events/recording-error)

[Next](/reference/rest-api/webhooks/events/transcript-ready-to-download)
