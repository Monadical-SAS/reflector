# Source: https://docs.daily.co/reference/rest-api/rooms/get-session-data

#

GET

/rooms/:name/get-session-data

Gets the meeting session data.

In the case of an error, returns an HTTP error with information about the error in the response body.

See the documentation for the in-call `setMeetingSessionData` [method](/reference/daily-js/instance-methods/set-meeting-session-data) for more information about how meeting session data works.

## Path params

`name`

string

The name of the room.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/send-app-message)

[Next](/reference/rest-api/rooms/set-session-data)
