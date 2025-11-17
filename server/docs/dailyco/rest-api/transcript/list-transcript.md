# Source: https://docs.daily.co/reference/rest-api/transcript/list-transcript

#

GET

/transcript

**A`GET` request to `/transcript` returns a list of transcripts for your domain.**

Transcripts are returned sorted by `created_at` time in reverse chronological order.

Each call to this endpoint fetches a maximum of 100 transcripts objects.

See our **[transcription guide](/guides/products/transcription)** for detailed information about transcribing calls with Daily. See our **[pagination reference](/reference/rest-api#pagination)** for how pagination works in API requests (and how to use the `limit`, `ending_before`, and `starting_after` query parameters).

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of transcripts stored (which, if [pagination](/reference/rest-api#pagination) arguments are supplied, could be greater than the number of transcripts returned by this query).

The `data` field is a list of transcripts objects.

## Query params

`limit`

int32

`ending_before`

string

`starting_after`

string

`roomId`

string

`mtgSessionId`

string

## Example request

### List transcripts

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/transcript/config)

[Next](/reference/rest-api/transcript/get-transcript-information)
