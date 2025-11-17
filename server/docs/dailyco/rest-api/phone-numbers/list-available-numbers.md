# Source: https://docs.daily.co/reference/rest-api/phone-numbers/list-available-numbers

#

GET

/list-available-numbers

[Pay-as-you-go](https://www.daily.co/pricing)

List an available phone number

## Query params

`areacode`

string

An areacode to search within.

`region`

string

A region or state to search within. Must be an ISO 3166-2 alpha-2 code, i.e. CA for California. Cannot be used in combination with areacode.

`city`

string

A specific City to search within. Example, New York. The string must be url encoded because it is a url parameter. Must be used in combination with region. Cannot be used in combination with areacode, starts_with, contains, or ends_with.

`contains`

string

A string of 3 to 7 digits that should appear somewhere in the number.

`starts_with`

string

A string of 3 to 7 digits that should be used as the start of a number. Cannot be used in combination with contains or ends_with.

`ends_with`

string

A string of 3 to 7 digits that should be used as the end of a number. Cannot be used in combination with starts_with or contains.

## Example request

**Request**

**200 OK**

**400 Validation Error**

**500 Vendor Unavailable**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/phone-numbers/buy-phone-number)
