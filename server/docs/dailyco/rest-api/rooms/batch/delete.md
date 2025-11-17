# Source: https://docs.daily.co/reference/rest-api/rooms/batch/delete

#

DELETE

/batch/rooms

The `DELETE /batch/rooms` endpoint allows you to delete many rooms with one API call, more efficiently and with higher effective rate-limits than deleting the rooms with multiple calls to the [`DELETE /rooms`](/reference/rest-api/rooms/delete-room) endpoint.

## Error behavior

If there is an error in any of the data passed to this endpoint, or if an error occurs while trying to delete the rooms, no rooms will be deleted.

## Limits

  * A maximum of 1000 rooms can be deleted per call to this endpoint



## Body params

## `rooms`

`room_names`

array

An array of room names to delete.

## Example requests

### Delete 2 rooms

**Request**

**200 OK**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/batch/post)

Next
