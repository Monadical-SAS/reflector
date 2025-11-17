# Source: https://docs.daily.co/reference/rest-api/webhooks/get-webhook

#

GET

/webhooks/:uuid

[Pay-as-you-go](https://www.daily.co/pricing)

**A`GET` request to `/webhooks/:uuid` returns your webhook. **

Returns the webhook at the given uuid.

`uuid`

string

The uuid of the webhook.

## Response Body Parameters

`uuid`

string

The unique identifier for this webhook.

`url`

string

The webhook server endpoint that was provided.

`hmac`

string

A secret that can be used to verify the signature of the webhook.

`basicAuth`

string

The basic auth credentials that will be used to POST to the webhook URL.

`retryType`

string

The retry configuration for this webhook endpoint to use. The default is circuit-breaker.

Options: "circuit-breaker","exponential"

`eventTypes`

array

The set of event types this webhook is subscribed to.

`state`

string

The current state of the webhook. "FAILED" | "INACTIVE"

`failedCount`

number

The number of consecutive failures this webhook has made.

`lastMomentPushed`

string

The ISO 8601 time of the last moment an event was pushed to the webhook server.

`domainId`

string

The domain ID this webhook is associated with.

`createdAt`

string

The ISO 8601 time of when this webhook was created.

`updatedAt`

string

The ISO 8601 time of when this webhook was last updated.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/get)

Next
