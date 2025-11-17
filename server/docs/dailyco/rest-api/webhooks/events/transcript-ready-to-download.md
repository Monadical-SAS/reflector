# Source: https://docs.daily.co/reference/rest-api/webhooks/events/transcript-ready-to-download

# Transcript Ready To Download

A transcript ready to download event is sent when a transcript enters a `finished` state with a non-zero duration. At this point, a transcript will exist in an S3 bucket for download. If an error ocurred during transcript, you will also receive a `transcript.error` event.

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

Options: "transcript.ready-to-download"

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

`room_id`

string

The ID of the room where the event occurred.

`mtg_session_id`

string

The meeting session ID related to the event.

`duration`

number

The duration of the session in seconds.

`participant_minutes`

number

The cumulative participant minutes for the transcription session.

`status`

string

The current status of the transcription event.

Options: "t_in_progress","t_finished","t_failed"

`domain_id`

string

The ID of the domain corresponding to this transcription event.

Copy to clipboard

;

* * *

[Previous](/reference/rest-api/webhooks/events/transcript-started)

[Next](/reference/rest-api/webhooks/events/transcript-error)
