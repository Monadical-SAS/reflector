# Source: https://docs.daily.co/reference/rest-api/webhooks/events/streaming-started

# Streaming Started

A streaming started event emits when Daily begins to stream a call. These can be activated via [`startLiveStreaming()`](/reference/daily-js/instance-methods/start-live-streaming) or via the [REST API](/reference/rest-api/rooms/live-streaming/start).

## Webhook Events

There are five common fields all events share:

`version`

string

Represents the version of the event. This uses [semantic versioning](https://semver.org/) to inform a consumer if the payload has introduced any breaking changes.

`type`

string

Represents the type of the event described in the payload.

`id`

string

An identifier representing this specific event.

`payload`

object

An object representing the event, whose fields are described below.

`event_ts`

number

Documenting when the webhook itself was sent. This timestamp is different than the time of the event the webhook describes. For example, a recording.started event will contain a start_ts timestamp of when the actual recording started, and a slightly later event_ts timestamp indicating when the webhook event was sent.

## Payload

`version`

string

The semantic version of the current message.

`type`

string

The type of event that is being provided.

Options: "streaming.started"

`event_ts`

number

The Unix epoch time in seconds representing when the event was generated.

`payload`

object

The payload of the object, describing the given event.

`timestamp`

integer

The Unix epoch time in seconds representing when streaming was started.

`instance_id`

string

The streaming instance ID.

`domain_id`

string

ID of the domain for which streaming was started.

`layout`

object

The layout used for streaming.

### Default Layout

`preset`

string

Options: "default"

`max_cam_streams`

number

### Single Participant Layout

`preset`

string

Options: "single-participant"

`session_id`

string

### Active Participant Layout

`preset`

string

Options: "active-participant"

### Portrait Layout

`preset`

string

Options: "portrait"

`variant`

string

Options: "vertical","inset"

`max_cam_streams`

number

### Custom Layout

`preset`

string

Options: "custom"

`composition_id`

string

`composition_params`

object

`session_assets`

object

Copy to clipboard

* * *

[Previous](/reference/rest-api/webhooks/events/transcript-error)

[Next](/reference/rest-api/webhooks/events/streaming-updated)
