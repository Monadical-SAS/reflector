# Source: https://docs.daily.co/reference/rest-api/rooms/send-app-message

#

POST

/rooms/:name/send-app-message

Sends a message to participants within a room.

Messages are delivered to participants currently in the call. They are not stored. If a recipient is not in the call when the message is sent, the recipient will never receive the message.

In the case of an error, returns an HTTP error with information about the error in the response body.

You can listen for these messages by installing a handler for the `app-message` [event](/reference/daily-js/events/participant-events#app-message).

## Path params

`name`

string

The name of the room.

## Body params

`data`

object

A javascript object that can be serialized into JSON. Data sent must be within the 4kb size limit.

`recipient`

string

Determines who will recieve the message. It can be either a participant session_id, or `*`. The `*` value is the default, and means that the message is a "broadcast" message intended for all participants.

Default: *

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/delete-room)

[Next](/reference/rest-api/rooms/get-session-data)
