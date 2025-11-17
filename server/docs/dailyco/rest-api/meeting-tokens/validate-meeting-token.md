# Source: https://docs.daily.co/reference/rest-api/meeting-tokens/validate-meeting-token

#

GET

/meeting-tokens/:meeting_token

**A`GET` request to `/meeting-tokens/:meeting_token` validates a meeting token.**

You can only validate tokens created for your domain.

If the token does not belong to your domain, or has an `exp` in the past, this endpoint will return an error.

If the token is currently valid and it belongs to your domain, this method returns an object that lists the token's properties.

If the token is not yet valid but will be in the future, meaning it has an `nbf` property, set the `ignoreNbf` query param to `true` to validate it.

## Path params

`meeting_token`

string

## Query params

`ignoreNbf`

boolean

Ignore the `nbf` in a JWT, if given

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/meeting-tokens/create-meeting-token)

Next
