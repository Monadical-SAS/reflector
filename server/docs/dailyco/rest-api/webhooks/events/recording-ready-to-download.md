# Source: https://docs.daily.co/reference/rest-api/webhooks/events/recording-ready-to-download

# Recording Ready To Download

A recording ready to download event is sent when a recording enters a `finished` state with a non-zero duration. At this point, a recording will exist in an S3 bucket for download. If an error ocurred during recording, you will also receive a `recording.error` event.

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

Options: "recording.ready-to-download"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`type`

string

The type of recording that was generated.

Options: "cloud","raw-tracks"

`recording_id`

string

An ID identifying the recording that was generated.

`room_name`

string

The name of the room where the recording was made.

`start_ts`

integer

The Unix epoch time in seconds representing when the recording started.

`status`

string

The status of the given recording.

Options: "finished"

`max_participants`

integer

The number of participants on the call that were recorded.

`duration`

integer

The duration in seconds of the call.

`s3_key`

string

The location of the recording in the provided S3 bucket.

`tracks`

array

If the recording is a raw-tracks recording, a tracks field will be provided. If role permissions have been removed, the tracks field may be null.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/recording-started)

[Next](/reference/rest-api/webhooks/events/recording-error)
