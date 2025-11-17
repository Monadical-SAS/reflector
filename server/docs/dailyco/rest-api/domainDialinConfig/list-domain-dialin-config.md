# Source: https://docs.daily.co/reference/rest-api/domainDialinConfig/list-domain-dialin-config

#

GET

/domain-dialin-config

**A`GET` request to `/domain-dialin-config` returns a list of all dialin configs for your domain.**

dialin configs are returned sorted by `created_at` time in reverse chronological order.

Each call to this endpoint fetches a maximum of 100 domain-dialin-config objects.

See our **[pinless/pin dialin guide](/guides/products/dial-in-dial-out/dialin-pinless)** for detailed information about pinless_dialin and pin_dialin with Daily. See our **[pagination reference](/reference/rest-api#pagination)** for how pagination works in API requests (and how to use the `limit`, `ending_before`, and `starting_after` query parameters).

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of configs stored (which, if [pagination](/reference/rest-api#pagination) arguments are supplied, could be greater than the number of domain-dialin-configs returned by this query).

The `data` field is a list of configs objects.

## Query params

`limit`

int32

`ending_before`

string

`starting_after`

string

`phone_number`

string

`phone_numbers`

string

`sip_username`

string

`name_prefix`

string

`type`

string

## Example request

### List transcripts

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/domainDialinConfig/get-domain-dialin-config)

[Next](/reference/rest-api/domainDialinConfig/delete-domain-dialin-config)
