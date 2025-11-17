# Source: https://docs.daily.co/reference/rest-api/batch-processor/reference/get-job

# Get job status

## GET /batch-processor/:id

This endpoint retrieves information of a previously submitted job (by id).

### Response definitions

Top-level:

Attribute Name| Type| Description| Example
---|---|---|---
`id`| `string`| The ID of the job| "3ab8faa2-8ba2-4ee6-bd15-003a92c18245"
`preset`| `string`| The preset given when submitting the job| "recordingId"
`status`| `string`| The status of the job: ["submitted", "processing", "finished", "error"]| "finished"
`input`| `object`| The input configuration| `{...}`
`output`| `object`| The output attributes| `{...}`
`error`| `string`| Details of error| "Error: Failed to transcribe. May be invalid audio or silent file"

In the `input` object:

Attribute Name| Type| Description| Example
---|---|---|---
`sourceType`| `string`| The `sourceType` given when submitting the job| "recordingId"
`recordingId`| `string`| The recording ID (when using this `sourceType`)| "uuiasdfe-8ba2-4ee6-bd15-003a92c18245"
`uri`| `string`| The video/audio link URL (when using this `sourceType`)| "https://direct-url-to/file.mp4"

In the `output` object:

Attribute Name| Type| Description| Example
---|---|---|---
`transcription`| `list`| A list of transcript outputs| `[...]`
`summary`| `object`| Output for the summary job| `{...}`

In the `output.transcription` list:

Attribute Name| Type| Description| Example
---|---|---|---
`format`| `string`| The filetype of the transcript| "txt"
`s3Config.key`| `string`| The S3 object location of the file| "bucket-name/uuiasdfe-8ba2-4ee6-bd15-003a92c18245/transcript/output.txt"
`s3Config.bucket`| `string`| The S3 bucket name| "bucket-name"
`s3Config.region`| `string`| The S3 region for the output| "us-west-2"

In the `output.summary` object:

Attribute Name| Type| Description| Example
---|---|---|---
`format`| `string`| The filetype of the summary| "txt"
`s3Config.key`| `string`| The S3 object location of the file| "your-daily-domain/uuiasdfe-8ba2-4ee6-bd15-003a92c18245/transcript/output.txt"
`s3Config.bucket`| `string`| The S3 bucket name| "bucket-name"
`s3Config.region`| `string`| The S3 region for the output| "us-west-2"

### Examples

**Request**

**200 OK (Job finished)**

**200 OK (Job error)**

Copy to clipboard

* * *

[Previous](/reference/rest-api/batch-processor/reference/submit-job)

[Next](/reference/rest-api/batch-processor/reference/get-job-access-link)
