# Source: https://docs.daily.co/reference/rest-api/rooms/get-room-presence

#

GET

/rooms/:name/presence

**A`GET` request to `/rooms/:name/presence` retrieves presence data about a specific room.**

This endpoint provides a snapshot of the presence of participants in a given room.

## Path params

`room_name`

The name of the room

## Query params

`limit`

Sets the number of participants returned.

`userId`

Returns presence for the user with the given userId, if available. The userId is specified via a [meeting token](/reference/rest-api/meeting-tokens/config#user_id).

`userName`

Returns presence for the user with the given name, if available.

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/get-room-config)

[Next](/reference/rest-api/rooms/set-room-config)
