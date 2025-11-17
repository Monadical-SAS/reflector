# Source: https://docs.daily.co/reference/rest-api/recordings/delete-recording

#

DELETE

/recordings/:id

**A`DELETE` request to `/recordings/:id` deletes a recording.**

If the requested recording is found and deleted, this API endpoint returns two fields in the response body: `deleted` (set to `true`), and the recording `id`.

If the recording is not found (and, therefore, cannot be deleted) the endpoint returns an HTTP 404 error.

This request does _not_ delete recordings from any custom S3 buckets configured by the customer for storage. If the recording is stored in a custom S3 bucket, the `DELETE` request only deletes the reference to it from Daily's database. The API response will contain the S3 bucket of the storage location, enabling the caller to provide their own logic to delete the recording from their S3 bucket.

## Path params

`recording_id`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/recordings/get-recording-information)

[Next](/reference/rest-api/recordings/get-recording-link)
