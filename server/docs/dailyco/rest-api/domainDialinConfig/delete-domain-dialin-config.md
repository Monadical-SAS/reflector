# Source: https://docs.daily.co/reference/rest-api/domainDialinConfig/delete-domain-dialin-config

#

DELETE

/domain-dialin-config/:id

**A`DELETE` request to `/domain-dialin-config/:id` deletes a pinless_dialin and pin_dialin.**

If the requested domain-dialin-config is found, it is deleted and the API returns a `200` in the response body.

If the domain-dialin-config is not found (and, therefore, cannot be deleted) the endpoint returns a `404` error.

## Path params

`id`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/domainDialinConfig/list-domain-dialin-config)

Next
