# Source: https://docs.daily.co/reference/rest-api/meetings/get-meeting-participants

#

GET

/meetings/:meeting/participants

**A`GET` request to `/meetings/:meeting/participants` returns information about participants in the specified meeting session.**

In order to paginate, you can use the `joined_after` field using the last participant id in the list. Once there are no more users remaining, you'll receive a `404` from the endpoint.

## Path params

`meeting`

the ID of the meeting session

## Query params

`limit`

the largest number of participant records to return

`joined_after`

limit to participants who joined after the given participant, identified by `participant_id`

`joined_before`

limit to participants who joined before the given participant, identified by `participant_id`

## Example request

### Get a meeting session

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/meetings/get-meetings-meeting)

Next
