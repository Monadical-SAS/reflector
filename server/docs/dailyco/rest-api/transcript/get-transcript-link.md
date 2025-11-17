# Source: https://docs.daily.co/reference/rest-api/transcript/get-transcript-link

#

GET

/transcript/:id/access-link

**A`GET` request to `/transcript/:id/access-link` creates and returns a transcript access link.**

  * The `link` is valid for one hour.
  * The `link` is a cryptographically signed, time-limited, direct link to a `.vtt` file stored on Amazon S3.
    * It is important to note, if certain error conditions occur (for instance, domain properties prevent access to transcript), this field could return a string rather than a URL.
  * For files stored in a [custom S3 bucket](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket), `access-link` download permissions are controlled by `allow_api_access` parameter for [transcription_bucket](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket).



## Path params

`transcriptId`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/transcript/delete-transcript)

Next
