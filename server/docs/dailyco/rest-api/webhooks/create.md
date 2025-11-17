# Source: https://docs.daily.co/reference/rest-api/webhooks/create

#

POST

/webhooks

[Pay-as-you-go](https://www.daily.co/pricing)

**A`POST` request to `/webhooks` creates a new webhook. **

Creates a new webhook. Returns an error if the webhook URL provided does not return a `200` status code within a few seconds. Upon creation, new sessions should begin to emit the events specified in the `eventTypes` field.

When creating a webhook via the `POST /webhooks` endpoint, Daily will send a request to the webhook server with a test request body. If we do not receive a `200` status code relatively quickly, we will consider the endpoint faulty and return a `400` error. It can be helpful to return a response immediately before handling the event to avoid webhook disruptions.

## Body params

`url`

string

The webhook server endpoint that was provided.

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

`hmac`

string

A secret that can be used to verify the signature of the webhook. If not provided, an hmac will be provisioned for you and returned.

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

[Previous](/reference/rest-api/webhooks/events)

[Next](/reference/rest-api/webhooks/update)
