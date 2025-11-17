# Source: https://docs.daily.co/reference/rest-api/rooms/delete-room

#

DELETE

/rooms/:name

**A`DELETE` request to `/rooms/:name` deletes a room.**

If the requested room is found and deleted, this API endpoint returns two fields in the response body: `deleted` (set to `true`), and the room `name`.

If the room is not found (and, therefore, cannot be deleted) the endpoint returns an HTTP 404 error.

If the room exists but its `exp` time has passed, the endpoint returns an HTTP error exactly as above, but with the addition of a `deleted` field, set to `true`. In general, expired rooms are treated by API endpoints as having been implicitly deleted. And, in fact, they will eventually be deleted by a collector process that runs periodically. But in rare cases you may want to know that your API call has deleted an expired room.

## Path params

`name`

string

Defaults to a randomly generated string A room name can include only the uppercase and lowercase ascii letters, numbers, dash and underscore. In other words, this regexp detects an invalid room name: /[^A-Za-z0-9_-]/.

The room name cannot exceed 128 characters. You'll get an error if you try to create a room with a name that's too long.

## Example requests

### Delete a room

**Request**

**200 OK**

Copy to clipboard

### Room not found to delete

**Request**

**404**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/set-room-config)

[Next](/reference/rest-api/rooms/send-app-message)
