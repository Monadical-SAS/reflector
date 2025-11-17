# Source: https://docs.daily.co/reference/rest-api/webhooks/update

#

POST

/webhooks/:uuid

[Pay-as-you-go](https://www.daily.co/pricing)

**A`POST` request to `/webhooks/:uuid` updates your webhook. **

This endpoint allows you to update the given webhook. You can subscribe to new events or alter your url. You can also use this endpoint to re-activate a webhook that has entered a failed state - just use the same `url` as before, and Daily will verify that the endpoint is connectable and turn the webhook back on.

When updating a webhook via the `POST /webhooks` endpoint, Daily will send a request to the webhook server with a test request body. If we do not receive a `200` status code relatively quickly, we will consider the endpoint faulty and return a `400` error. It can be helpful to return a response immediately before handling the event to avoid webhook disruptions.

## Path params

`uuid`

string

The uuid of the webhook.

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

A secret that can be used to verify the signature of the webhook.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/create)

[Next](/reference/rest-api/webhooks/delete)
