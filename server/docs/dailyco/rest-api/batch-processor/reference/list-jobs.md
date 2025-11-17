# Source: https://docs.daily.co/reference/rest-api/batch-processor/reference/list-jobs

# Get list of jobs

## GET /batch-processor

This endpoint retrieves a list of jobs that were submitted to the batch processor.

### Request parameters

This endpoint supports the same [pagination and filtering](/reference/rest-api#pagination) options as other endpoints. Additional paramters are listed in the following table:

Query parameter| Description| Default| Example
---|---|---|---
`recordingId`| Filters jobs by a recording id| `null`| uuiasdfe-8ba2-4ee6-bd15-003a92c18245

### Response definitions

Top-level:

Attribute Name| Type| Description| Example
---|---|---|---
`total_count`| `integer`| The total count of the query| 10
`data`| `list`| List of jobs| `[...]`

In the `data` object:

Attribute Name| Type| Description| Example
---|---|---|---
`id`| `string`| The id of the job| "3ab8faa2-8ba2-4ee6-bd15-003a92c18245"
`preset`| `string`| The preset given when submitting the job| "recordingId"
`status`| `string`| The status of the job. One of: ["submitted", "processing", "finished", "error"]| "finished"

### Examples

**Request**

**200 OK**

Copy to clipboard

* * *

[Previous](/reference/rest-api/batch-processor/reference/get-job-access-link)

[Next](/reference/rest-api/batch-processor/reference/delete-job)
