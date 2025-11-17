# Source: https://docs.daily.co/reference/rest-api/rooms/batch/post

#

POST

/batch/rooms

The `POST /batch/rooms` endpoint allows you to create many rooms with one API call, more efficiently and with higher effective rate-limits than creating the rooms with multiple calls to the [`POST /rooms`](/reference/rest-api/rooms/create-room) endpoint.

## Error behavior

If there is an error in any of the data passed to this endpoint, or if an error occurs while trying to create the rooms, no rooms will be created.

## Limits

  * A maximum of 1000 rooms can be created per call to this endpoint
  * Only 10 different [recording bucket configurations](/reference/rest-api/rooms/create-room#recordings_bucket) can be specified across the rooms to be created. The same recording bucket configuration can be specified multiple times without limit.



## Body params

## `rooms`

`rooms`

array

An array of [room configuration](/reference/rest-api/rooms/config) objects.

## Example requests

### Create 2 rooms with random names and default privacy and properties

**Request**

**200 OK**

Copy to clipboard

### Create 2 rooms with specified names that expire in two hours

**Request**

**200 OK**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/rooms/batch/delete)
