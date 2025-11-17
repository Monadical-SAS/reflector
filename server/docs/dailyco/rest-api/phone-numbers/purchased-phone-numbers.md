# Source: https://docs.daily.co/reference/rest-api/phone-numbers/purchased-phone-numbers

#

GET

/purchased-phone-numbers

[Pay-as-you-go](https://www.daily.co/pricing)

List the purchased phone numbers for this domain.

Each call to this endpoint fetches a maximum of 50 recording objects.

See our **[pagination reference](/reference/rest-api#pagination)** for how pagination works in API requests (and how to use the `limit`, `ending_before`, and `starting_after` query parameters).

The response body consists of two fields: `total_count` and `data`.

The `total_count` field is the total number of phoneNumbers stored (which, if [pagination](/reference/rest-api#pagination) arguments are supplied, could be greater than the number of phone numbers returned by this query).

The response message has a `pagination_id` field, which should be used for the pagination in the `starting_after` and `ending_before`

The `data` field is a list of phoneNumber objects.

## Query params

`limit`

int32

`ending_before`

string

`starting_after`

string

`filter_name`

string

`filter_number`

string

## Example request

**Request**

**200 OK**

Copy to clipboard

* * *

[Previous](/reference/rest-api/phone-numbers/release-phone-number)

Next
