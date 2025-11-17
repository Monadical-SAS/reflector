# Source: https://docs.daily.co/reference/rest-api/recordings/list-recordings

#

GET

/recordings

**A`GET` request to `/recordings` returns a list of cloud recordings for your domain.**

Recordings are returned sorted by `created_at` time in reverse chronological order.

Each call to this endpoint fetches a maximum of 100 recording objects.

See our **[recording guide](/guides/recording-calls-with-the-daily-api)** for detailed information about recording calls with Daily. See our **[pagination reference](/reference/rest-api#pagination)** for how pagination works in API requests (and how to use the `limit`, `ending_before`, and `starting_after` query parameters).

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of recordings stored (which, if [pagination](/reference/rest-api#pagination) arguments are supplied, could be greater than the number of recordings returned by this query).

The `data` field is a list of recording objects.

## Query params

`limit`

int32

`ending_before`

string

`starting_after`

string

`room_name`

string

## Example request

### List recordings

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/recordings/config)

[Next](/reference/rest-api/recordings/get-recording-information)
