# Source: https://docs.daily.co/reference/rest-api/phone-numbers/buy-phone-number

#

POST

/buy-phone-number

This will buy a phone number. In the POST request you can either provide the phone number you want to buy, or leave it empty. If the specified `number` is still available, it will be bought or the API will return a failure. Alternatively, if you skipped the `number` field, a random phone number from California (CA) will be bought.

You can check or find available numbers using the [list-available-numbers](/reference/rest-api/phone-numbers/list-available-numbers) API.

## Body params

`number`

string

The phone number to purchase

## Response Body

The response body contains two fields, an `id` and a `number`.

  * `id`: a UUID that uniquely identifies this phone-number. Will need this ID for deleting the phone-number
  * `number`: the purchased phone-number, for example, if a random was requested.



## Example request

**Request**

**200 OK**

Copy to clipboard

* * *

[Previous](/reference/rest-api/phone-numbers/list-available-numbers)

[Next](/reference/rest-api/phone-numbers/release-phone-number)
