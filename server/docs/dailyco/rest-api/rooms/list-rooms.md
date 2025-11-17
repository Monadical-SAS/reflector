# Source: https://docs.daily.co/reference/rest-api/rooms/list-rooms

#

GET

/rooms

**A`GET` request to `/rooms` returns a list of rooms in your domain.**

Rooms are returned sorted by `created_at_time` in reverse chronological order (your most recent room comes first; oldest latest).

Each call to this endpoint fetches a maximum of 100 room objects.

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of rooms in the domain. The count includes rooms outside the scope of the request, e.g. if you’ve created +100 rooms, exceeding the request limit, or if you’ve provided `started_before` or `ending_before` arguments.

The `data` field is a list of room objects.

## Query params

`limit`

int32

Sets the number of rooms listed

`ending_before`

string

Returns room objects created before a provided room id

`starting_after`

string

Returns room objects created after a provided room id

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

When a room object is returned by an API call, only configuration options that differ from the defaults are included in the config struct.

**Further reading**

  * [Room configuration](/reference/rest-api/rooms/config)
  * How to use the `limit`, `ending_before`, and `starting_after` [query parameters](/reference/rest-api#pagination)



* * *

[Previous](/reference/rest-api/rooms/config)

[Next](/reference/rest-api/rooms/create-room)
