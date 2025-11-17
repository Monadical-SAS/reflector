# Source: https://docs.daily.co/reference/rest-api/webhooks/events/batch-processor-job-finished

# Job Finished

A batch processor job finished event is emitted when as batch processor job enters the `finished` status. Read more about batch processor jobs [here](/reference/rest-api/batch-processor).

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

Options: "finished"

`input`

object

These parameters define what the inputs were for this given batch processor job.

`sourceType`

string

The source type describing the input of the job.

Options: "recordingId","uri","transcriptUri"

`uri`

string

If `uri` or `transcriptUri` `sourceType`, this field represents the uri to access the content (transcript, video or audio file).

`recordingId`

string

If `recordingId` `sourceType`, this field represents the id of the recording.

`language`

string

If `uri` `sourceType`, this field represents the BCP-47 language of the transcript.

`output`

object

These parameters define the output of the batch processor job.

`soap`

object

If this job generated a SOAP output, this field will be defined.

`format`

string

The filetype of this SOAP note.

Options: "JSON"

`s3Config`

object

The S3 bucket configuration for this file.

`bucket`

string

The s3 bucket containing this file.

`key`

string

The s3 object location of this file.

`region`

string

The s3 bucket region.

`concept`

object

If this job generated concepts output, this field will be defined.

`format`

string

The filetype of these concepts.

Options: "JSON"

`s3Config`

object

The S3 bucket configuration for this file.

`bucket`

string

The s3 bucket containing this file.

`key`

string

The s3 object location of this file.

`region`

string

The s3 bucket region.

`summary`

object

If this job generated summary output, this field will be defined.

`format`

string

The filetype of this summary.

Options: "txt"

`s3Config`

object

The S3 bucket configuration for this file.

`bucket`

string

The s3 bucket containing this file.

`key`

string

The s3 object location of this file.

`region`

string

The s3 bucket region.

`transcription`

array

If this job generated transcriptions output, this field will be defined.

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/streaming-error)

[Next](/reference/rest-api/webhooks/events/batch-processor-error)
