# Source: https://docs.daily.co/reference/rest-api/rooms/set-session-data

#

POST

/rooms/:name/set-session-data

Sets the meeting session data, which will be synced to all participants within a room.

In the case of an error, returns an HTTP error with information about the error in the response body.

See the documentation for the in-call `setMeetingSessionData` [method](/reference/daily-js/instance-methods/set-meeting-session-data) for more information about how meeting session data works.

## Path params

`name`

string

The name of the room.

## Body params

`data`

object

A javascript object that can be serialized into JSON. Defaults to `{}`.

`mergeStrategy`

string

`replace` to replace the existing meeting session data object or `shallow-merge` to merge with it.

Options: "replace","shallow-merge"

Default: replace

`keysToDelete`

array

Optional list of keys to delete from the existing meeting session data object when using `shallow-merge`.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/get-session-data)

[Next](/reference/rest-api/rooms/eject)
