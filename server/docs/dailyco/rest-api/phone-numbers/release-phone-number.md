# Source: https://docs.daily.co/reference/rest-api/phone-numbers/release-phone-number

#

DELETE

/release-phone-number/:id

[Pay-as-you-go](https://www.daily.co/pricing)

**A`DELETE` request to `/release-phone-number/:id` releases the the specified phone number referenced by its `id`.**

A number cannot be deleted within the 14 days of purchase. Calling this API before this period expires results in an error.

## Path params

`id`

string

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/phone-numbers/buy-phone-number)

[Next](/reference/rest-api/phone-numbers/purchased-phone-numbers)
