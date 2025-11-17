# Source: https://docs.daily.co/reference/rest-api/meetings/get-meeting-information

#

GET

/meetings

**A`GET` request to `/meetings` returns a list of meeting sessions.**

Meeting sessions are returned sorted by `start_time` time in reverse chronological order.

Results can be filtered by supplying any of `room`, `timeframe_start`, and `timeframe_end` arguments.

Each call to this endpoint fetches a maximum of 100 meeting session objects.

See [Nuts and Bolts: Pagination](/reference/rest-api#pagination) for how pagination works in API requests (and how to use the `limit`, `ending_before`, and `starting_after` query parameters).

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of meeting session objects that match the query, including the filtering by `room`, `timeframe_start`, and `timeframe_end`, but ignoring pagination arguments. (In other words, if pagination arguments are supplied, `total_count` could be greater than the number of meeting session objects returned by this query).

The `data` field is a list of meeting session objects. Each meeting session object includes the `id`, `room` (room name), `start_time`, `duration` (in seconds), a boolean that describes whether the meeting is `ongoing`, and a [`participants` object](/reference/daily-js/instance-methods/participants) of all meeting attendees.

**Granularity of timestamps**

The `start_time`, `join_time`, and `duration` fields are accurate to approximately 15 seconds. We don't write a "meeting join" record into our database until a user has stayed in a room for at least 10 seconds.

In general, we try to slightly undercount usage, to make sure we're not overcharging you for meeting participant-minutes!

## Query params

`room`

string

`timeframe_start`

integer

`timeframe_end`

integer

`limit`

integer

`starting_after`

string

`ending_before`

string

`ongoing`

boolean

`no_participants`

boolean

The optional `room` argument should be a room name, and limits results to that room.

The optional `timeframe_start` argument is a unix timestamp, and limits results to meeting sessions that have a `start_time` greater than or equal to `timeframe_start`.

The optional `timeframe_end` argument is a unix timestamp, and limits results to meeting sessions that have a `start_time` less than `timeframe_end`.

The optional `ongoing` argument is a boolean value. If set to `true`, it limits results to meetings where participants are currently in the room. If set to `false`, it limits the results to meetings where there are no participants remaining in the room.

The optional `no_participants` argument is a boolean value. If set to `true`, this endpoint won't return the participant list in each meeting. This is useful for meetings with large numbers of participants. You can use the [meetings/:meeting/participants](/reference/rest-api/meetings/get-meeting-participants) endpoint to retrieve a paginated list of participants for a given meeting.

## Example request

### Get meeting sessions for a specific room and time frame

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/meetings/get-meetings-meeting)
