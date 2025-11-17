# Source: https://docs.daily.co/reference/rest-api/transcript/delete-transcript

#

DELETE

/transcript/:id

**A`DELETE` request to `/transcript/:id` deletes a transcript.**

If the requested transcript is found and deleted, this API endpoint returns a `200` with the response body.

If the transcript is not found (and, therefore, cannot be deleted) the endpoint returns a `404` error.

This request does _not_ delete transcript from any custom S3 buckets configured by the customer for storage. If the transcript is stored in a custom S3 bucket, the `DELETE` request only deletes the reference to it from Daily's database. The API response will contain the S3 bucket of the storage location, enabling the caller to provide their own logic to delete the recording from their S3 bucket.

## Path params

`transcriptId`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/transcript/get-transcript-information)

[Next](/reference/rest-api/transcript/get-transcript-link)
