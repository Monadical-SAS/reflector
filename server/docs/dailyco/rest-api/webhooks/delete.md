# Source: https://docs.daily.co/reference/rest-api/webhooks/delete

#

DELETE

/webhooks/:uuid

[Pay-as-you-go](https://www.daily.co/pricing)

**A`DELETE` request to `/webhooks/:uuid` deletes your webhook. **

Deletes the given webhook. The webhook will immediately become inactive and no further events will be sent to the endpoint.

## Path params

`uuid`

string

The uuid of the webhook.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/update)

[Next](/reference/rest-api/webhooks/get)
