# Source: https://docs.daily.co/reference/rest-api/webhooks

# Listen for webhooks

Add a credit card to your account to unlock access to webhooks.

[Webhooks](https://webhooks.fyi/) are a helpful way to receive notifications about events that are occuring in Daily. In order to use webhooks, you'll need to create a web server with an endpoint that Daily can `POST` requests to as they occur. This allows you to track events in a more asynchronous and real-time fashion, instead of polling with API requests.

## Available webhook endpoints

  * [Create a webhook](/reference/rest-api/webhooks/create)
  * [Delete a webhook](/reference/rest-api/webhooks/delete)
  * [Get webhooks](/reference/rest-api/webhooks/get)
  * [Get webhook info](/reference/rest-api/webhooks/get-webhook)
  * [Update a webhook](/reference/rest-api/webhooks/update)



## Configuring Webhooks

In order to configure a webhook, you'll need to create a HTTP server. You can use an online service like [webhook.site](https://www.webhook.site) for testing, or test locally using a a service like [ngrok](https://www.ngrok.com).

When an asynchronous event occurs, we'll send a `POST` request to an endpoint you provide containing a request body that details the event. Once you have a server set up with an accompanying endpoint, you can send that to the `POST /webhooks` endpoint to create a webhook. Webhook events are sent for all rooms on your domain.

Copy to clipboard

Before creating your webhook, we perform a verification check to ensure your endpoint is active and capable of handling webhook events.

We'll send a `POST` request to your webhook endpoint with the following payload:

Copy to clipboard

If your endpoint returns a 200 status code, we will proceed to create your webhook. The response to the initial creation request will include details of the newly created webhook, such as its ID and event subscriptions.

Copy to clipboard

When creating a webhook via the `POST /webhooks` endpoint, Daily will send a request to the webhook server with a test request body. If we do not receive a `200` status code relatively quickly, we will consider the endpoint faulty and return a `400` error. It can be helpful to return a response immediately before handling the event to avoid webhook disruptions.

The webhooks service will return an `hmac` secret that you can use to verify the signature of a webhook. You may also pass in an `hmac` during a `create` or `update` request, if you'd like to specify your own secret. This secret must be BASE-64 encoded.

At this point, you can use the `uuid` field and the `GET /webhooks/:uuid` endpoint to receive information about your webhook.

Copy to clipboard

Copy to clipboard

## Webhook Structure

### `state`

Webhooks have a `state` field that may either be `"FAILED"` or `"ACTIVE"`.

Your webhook may enter the `FAILED` state if we fail to send an event to your webhook server 3 times. Succesful attempts will reset this counter. We require your webhook server to send a `200` status code relateively quickly, so be sure to respond to the request as soon as you receive it. See `retryType` for an alternative error handling behavior.

If your webhook has entered a failed state, we will no longer send events to that webhook. You can re-activate a webhook by sending a `POST` request to `/webhooks/:uuid`, where `uuid` is your webhook uuid. This will once again send a test message to the endpoint provided, and if a `200` is returned, we will re-activate the webhook.

You may also update the other webhook fields such as `eventTypes` if needed with this endpoint.

### `hmac`

The `hmac` field contains a secret that is shared between Daily and you. Ensure that you do not share this secret publicly, otherwise you will not be able to verify that an event came from Daily.

Webhooks provide an `hmac`, which is a BASE-64 encoded HMAC-sha256 secret that allows you to verify that the event in question actually came from Daily. You may also provide your own secret when creating a webhook, as long as it is BASE-64 encoded. When `POST`ing to your webhook server, Daily will provide two headers: `X-Webhook-Signature` and `X-Webhook-Timestamp`.

In order to verify the signature yourself, you'll need to compute the signature in a manner provided in the snippet below:

Copy to clipboard

`event` is the response body from the event that was `POST`ed to your webhook server. From there, you can sign the content with the `HMAC-sha256` string, and ensure that your signature matches the one in the `X-Webhook-Signature` header. As only Daily and you hold the `hmac`, this comparison ensures that the request came from Daily.

### `failedCount`

This is incremented every time Daily fails to send an event to the given webhook endpoint. This can happen if your server is not responding quickly enough or if it is returning a non-`200` status code. When this happens 3 times, the webhook will enter the `FAILED` state. If we have a succesful response at any time before this we will reset your `failedCount` to 0. Thus, intermittent failures should not cause the circuit breaker to flip.

### `basicAuth`

You may provide a `basicAuth` field when creating a webhook if you'd like Daily to send an `Authorization` header with a `Basic {secret}` value. This can be checked by your endpoint and used as an additional shared secret to ensure that you are only processing verified events from Daily.

### `retryType`

There are currently two retry type configurations available. `circuit-breaker` is the default. You can pass this field when creating a webhook, or updating a webhook.

#### `circuit-breaker`

This is the default retry type. Every message is treated equally, and is tried at least once. Each failure to your webhook server is counted, and if it ever reaches 3 failures or greater, a circuit breaker is flipped. At this point, Daily will stop attempting to send webhooks to the server. You can close the circuit breaker by sending a `POST` request to `/webhooks/:uuid`, which will attempt to send a request to your server again. If your server resolves correctly, Daily will begin sending events.

#### `exponential`

This retry is message based, instead of the global count that `circuit-breaker` uses. While `failedCount` is still incremented, Daily will never circuit break under this retry type. Each message will be retried at most 5 times, with an exponential backoff up to 15 minutes. If a message fails being sent 5 times, it will be deleted and no longer retried.

## Webhook Events

We provide several webhook events that you can subscribe to. See the [webhook events index](/reference/rest-api/webhooks/events) for more details.

  * [`meeting.started`](/reference/rest-api/webhooks/events/meeting-started)
  * [`meeting.ended`](/reference/rest-api/webhooks/events/meeting-ended)
  * [`participant.joined`](/reference/rest-api/webhooks/events/participant-joined)
  * [`participant.left`](/reference/rest-api/webhooks/events/participant-left)
  * [`waiting-participant.joined`](/reference/rest-api/webhooks/events/waiting-participant-joined)
  * [`waiting-participant.left`](/reference/rest-api/webhooks/events/waiting-participant-left)
  * [`recording.started`](/reference/rest-api/webhooks/events/recording-started)
  * [`recording.ready-to-download`](/reference/rest-api/webhooks/events/recording-ready-to-download)
  * [`recording.error`](/reference/rest-api/webhooks/events/recording-error)
  * [`transcript.started`](/reference/rest-api/webhooks/events/transcript-started)
  * [`transcript.ready-to-download`](/reference/rest-api/webhooks/events/transcript-ready-to-download)
  * [`transcript.error`](/reference/rest-api/webhooks/events/transcript-error)
  * [`streaming.started`](/reference/rest-api/webhooks/events/streaming-started)
  * [`streaming.updated`](/reference/rest-api/webhooks/events/streaming-updated)
  * [`streaming.ended`](/reference/rest-api/webhooks/events/streaming-ended)
  * [`streaming.error`](/reference/rest-api/webhooks/events/streaming-error)
  * [`batch-processor.job-finished`](/reference/rest-api/webhooks/events/batch-processor-job-finished)
  * [`batch-processor.error`](/reference/rest-api/webhooks/events/batch-processor-error)
  * [`dialout.connected`](/reference/rest-api/webhooks/events/dialout-connected)
  * [`dialout.answered`](/reference/rest-api/webhooks/events/dialout-answered)
  * [`dialout.stopped`](/reference/rest-api/webhooks/events/dialout-stopped)
  * [`dialout.warning`](/reference/rest-api/webhooks/events/dialout-warning)
  * [`dialout.error`](/reference/rest-api/webhooks/events/dialout-error)
  * [`dialin.ready`](/reference/rest-api/webhooks/events/dialin-ready)
  * [`dialin.connected`](/reference/rest-api/webhooks/events/dialin-connected)
  * [`dialin.stopped`](/reference/rest-api/webhooks/events/dialin-stopped)
  * [`dialin.warning`](/reference/rest-api/webhooks/events/dialin-warning)
  * [`dialin.error`](/reference/rest-api/webhooks/events/dialin-error)


