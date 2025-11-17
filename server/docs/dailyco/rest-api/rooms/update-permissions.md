# Source: https://docs.daily.co/reference/rest-api/rooms/update-permissions

#

POST

/rooms/:name/update-permissions

Updates permissions for participants in an ongoing meeting.

In the case of an error, returns an HTTP error with information about the error in the response body.

See the documentation for the in-call `updateParticipant` [method](/reference/daily-js/instance-methods/update-participant#permissions) for more details about participant permissions.

## Path params

`name`

string

The name of the room.

## Body params

`data`

object

Each key-value pair in the `data` object defines a set of permission updates to apply to a given participant. To specify a specific participant, use the participant id as the key in the data object, with the value being the object described below. You can also apply an update to all participants except those specified explicitly by using the key `"*"` instead of a participant id.

The value of each pair is an object containing some or all of the following properties:

Attribute Name| Type| Description| Example
---|---|---|---
`hasPresence`| `boolean`| Determines whether the participant is "present" or "hidden"| false
`canSend `| `boolean` or `array`| Array of strings identifying which types of media the participant can send or a boolean to grant/revoke permissions for all media types.| ['video', 'audio']
`canReceive`| `object`| Object specifying which media the participant should be permitted to receive. [See here for `canReceive` object format](/reference/daily-js/instance-methods/participants#permissionscanreceive-properties).| { base: false }
`canAdmin`| `boolean` or `array`| Array of strings identifying which types of admin tasks the participant can do or a boolean to grant/revoke permissions for all types.| ['participants']

When you provide one or more of `canSend`, `hasPresence`, or `canAdmin`, the provided permission completely overwrites whatever value the participant previously had for that permission. When you provide `canReceive`, the provided sub-fields—`base`, `byUserId`, or `byParticipantId`—overwrites the previous values of the corresponding `canReceive` sub-fields. If you omit any permission field, the corresponding participant permission won't be changed.

See the documentation for the in-call `updateParticipant` [method](/reference/daily-js/instance-methods/update-participant#permissions) for the allowed permissions values.

## Example requests

**Request**

**200 OK**

**404 not found**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/eject)

[Next](/reference/rest-api/rooms/recordings)
