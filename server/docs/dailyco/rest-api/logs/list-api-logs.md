# Source: https://docs.daily.co/reference/rest-api/logs/list-api-logs

#

GET

/logs/api

**A`GET` request to `/logs/api` returns a list of REST API logs.**

## Query params

`starting_after`

string

Given the log ID, will return all records after that ID. See [pagination docs](../../rest-api#pagination)

`ending_before`

string

Given the log ID, will return all records before that ID. See [pagination docs](../../rest-api#pagination)

`limit`

integer

Limit the number of logs and/or metrics returned

Default: 20

`source`

string

The source of the given logs, either `"api"` or `"webhook"`

Default: "api"

`url`

string

Either the webhook server URL, or the API endpoint that was logged

## Response Body Parameters

`id`

string

An ID identifying the log that was generated.

`userId`

string

The user ID associated with the owner of the account.

`domainId`

string

The domain ID associated with this log statement.

`source`

string

The source of this log statement. This will be `"api"` or `"webhook"`.

`ip`

string

The originating IP address of this request.

`method`

string

The HTTP method used for this request.

`url`

string

The API route that was queried.

`status`

string

The HTTP status code returned by the endpoint.

`createdAt`

string

The timestamp representing when the record was created.

`request`

string

A JSON string representing the request body of this API request.

`response`

string

A JSON string representing the response body of this API request.

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/logs/list-logs)

Next
