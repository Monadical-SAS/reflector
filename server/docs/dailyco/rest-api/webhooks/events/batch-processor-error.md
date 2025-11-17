# Source: https://docs.daily.co/reference/rest-api/webhooks/events/batch-processor-error

# Job Error

A batch processor error event is emitted when as batch processor job enters the `error` status. Read more about batch processor jobs [here](/reference/rest-api/batch-processor).

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

Options: "batch-processor.job-finished"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`id`

string

The batch processor job id.

`preset`

string

The preset given when starting the job.

`status`

string

The status of the job.

Options: "error"

`input`

object

These parameters define what the inputs were for this given batch processor job.

`sourceType`

string

The source type describing the input of the job.

Options: "recordingId","uri","transcriptUri"

`uri`

string

If the `sourceType` is `uri` or `transcriptUri`, this field represents the uri to access the content (transcript, video or audio file).

`recordingId`

string

If the `sourceType` is `recordingId`, this field will be present containing the recording ID provided.

`language`

string

If the `sourceType` is `uri`, this field represents the BCP-47 language of the transcript.

`error`

string

A description of the error that occurred.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/batch-processor-job-finished)

[Next](/reference/rest-api/webhooks/events/dialout-connected)
