# Source: https://docs.daily.co/reference/rest-api/rooms/eject

#

POST

/rooms/:name/eject

Ejects participants from an ongoing meeting. In the case of success, the ids of ejected participants are returned in `ejectedIds`. If one or more participants are not found, the call is still considered successful - examine the `ejectedIds` value to determine exactly which participants were ejected.

In the case of an error, returns an HTTP error with information about the error in the response body.

The participants to be ejected may be identified by participant id or by the `user_id` specified in a [meeting token](https://docs.daily.co/reference/rest-api/meeting-tokens). If `ban` is `true`, any `user_id` values given are remembered while the meeting is active, and participants are prevented from (re)joining with that `user_id`. (The lists of "banned" `user_id`s are not guaranteed to persist forever - they are stored in memory in running servers and some operations, such as software updates, reset the lists. But for most practical purposes, this mechanism may be used to prevent unwanted users from rejoining a meeting.)

See the documentation for the in-call `updateParticipant` [method](/reference/daily-js/instance-methods/update-participant) for an alternative mechanism for ejecting participants.

## Path params

`name`

string

The name of the room.

## Body params

`ids`

array

List of participant ids (max 100) to eject from the existing meeting session.

`user_ids`

array

List of user_ids (max 100) to eject from the existing meeting session.

`ban`

boolean

If true, participants are prevented from (re)joining with the given user_ids.

Default: false

## Example requests

**Request**

**200 OK**

**404 not found**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/set-session-data)

[Next](/reference/rest-api/rooms/update-permissions)
