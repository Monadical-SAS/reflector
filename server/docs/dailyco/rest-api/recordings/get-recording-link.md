# Source: https://docs.daily.co/reference/rest-api/recordings/get-recording-link

#

GET

/recordings/:id/access-link

**A`GET` request to `/recordings/:id/access-link` creates and returns a recording access link.**

The `valid_for_secs` query parameter is optional, and specifies the number of seconds into the future this link will remain valid for. If not provided as a parameter, `valid_for_secs` defaults to `3600` seconds (one hour). Due to constrains on STS Token validity duration, recording links at max be valid for 12 hours, and minimum for 15 mins for recordings stored in customers bucket.

The response body for a successful request contains an object with two properties: `download_link`, and `expires`.

The `download_link` is a cryptographically signed, time-limited, direct link to a `.mp4` file stored on Amazon S3. (The specific fact of S3 storage should be considered an implementation detail, which might change in the future.) Note that if certain error conditions occur (for instance, domain properties prevent access to recordings), this field could be an error string rather than a URL.

The `expires` property is a unix timestamp after which the `download_link` will no longer work.

For files stored in Daily's S3 bucket, the returned link has the `Content-Disposition` header set to `attachment`. Therefore, the recording will not be playable directly in the browser; instead, it will be downloaded to the local machine.

For files stored in a [custom S3 bucket](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket), the `Content-Disposition` header can be controlled by the `allow_streaming_from_bucket` parameter.

  * When `allow_streaming_from_bucket` is `true`, the header will be set to `Content-Dispostion: inline`. Therefore, the recording can be played directly in the browser.
  * When `allow_streaming_from_bucket` is `false`, the header will be set to `Content-Dispostion: attachment`. Therefore, the recording will be downloaded to the local machine as a file.



## Path params

`recording_id`

string

## Query param

`valid_for_secs`

int

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

This method has no side effects on the server. (That's why it's a `GET` request rather than a `POST` request.)

* * *

[Previous](/reference/rest-api/recordings/delete-recording)

Next
