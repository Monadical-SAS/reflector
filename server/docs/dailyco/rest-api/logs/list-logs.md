# Source: https://docs.daily.co/reference/rest-api/logs/list-logs

#

GET

/logs

**A`GET` request to `/logs` returns a list of logs filtered by the provided query paramaters.**

## Query params

`includeLogs`

boolean

If true, you get a "logs" array in the results

Default: true

`includeMetrics`

boolean

If true, results have "metrics" array

Default: false

`userSessionId`

string

Filters by this user ID (aka "participant ID"). Required if `mtgSessionId` is not present in the request

`mtgSessionId`

string

Filters by this Session ID. Required if `userSessionId` is not present in the request

`logLevel`

string

Filters by the given log level name

Options: "ERROR","INFO","DEBUG"

`order`

string

ASC or DESC, case insensitive

Default: DESC

`startTime`

integer

A JS timestamp (ms since epoch in UTC)

`endTime`

integer

A JS timestamp (ms since epoch), defaults to the current time

`limit`

integer

Limit the number of logs and/or metrics returned

Default: 20

`offset`

integer

Number of records to skip before returning results

Default: 0

## Example request

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/logs/config)

[Next](/reference/rest-api/logs/list-api-logs)
