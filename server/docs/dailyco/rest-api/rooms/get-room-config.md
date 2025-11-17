# Source: https://docs.daily.co/reference/rest-api/rooms/get-room-config

#

GET

/rooms/:name

**A`GET` request to `/rooms/:name` retrieves a [room object](/reference/rest-api/rooms).**

When a room object is returned by an API call, only configuration options that differ from the defaults are included in the config struct.

**Heads up!**

See [room configuration](/reference/rest-api/rooms/config) for a discussion of the room object and a table of all room configuration options.

## Path params

`room_name`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/create-room)

[Next](/reference/rest-api/rooms/get-room-presence)
