# Source: https://docs.daily.co/reference/rest-api/batch-processor/reference/get-job-access-link

# Get output from a job

## GET /batch-processor/:id/access-link

This endpoint creates links where you can download your batch processing outputs for the given job ID. The API will return HTTP 404 if the job ID does not exist. It returns HTTP 400 if the job status is not `finished`.

### Response definitions

Top-level:

Attribute Name| Type| Description| Example
---|---|---|---
`id`| `string`| The ID of the job| "3ab8faa2-8ba2-4ee6-bd15-003a92c18245"
`preset`| `string`| The preset given when submitting the job| "recordingId"
`status`| `string`| The status of the job. One of: ["submitted", "processing", "finished", "error"]| "finished"
`transcription`| `list`| List of transcript access-links| `[...]`
`summary`| `object`| The summary outputs access-link from summarize job| `{...}`

In the `transcription` list:

Attribute Name| Type| Description| Example
---|---|---|---
`format`| `string`| The filetype of the transcript| "txt"
`link`| `string`| The access-link to the output file| "[https://access-link-url.tld/file.txt"](https://access-link-url.tld/file.txt%22)

In the `summary` object:

Attribute Name| Type| Description| Example
---|---|---|---
`format`| `string`| The filetype of the summary| "txt"
`link`| `string`| The access-link to the output file| "[https://access-link-url.tld/file.txt"](https://access-link-url.tld/file.txt%22)

### Examples

**Request**

**200 OK (transcript)**

**200 OK (summary)**

Copy to clipboard

* * *

[Previous](/reference/rest-api/batch-processor/reference/get-job)

[Next](/reference/rest-api/batch-processor/reference/list-jobs)
