# Source: https://docs.daily.co/reference/rest-api/transcript/config

# Configuration

`transcriptId`

string

A unique, opaque ID for this object. You can use this ID in API calls, and in paginated list operations.

`domainId`

string

The Id of the [domain](https://docs.daily.co/reference/rest-api/your-domain).

`roomId`

string

The id of the [room](https://docs.daily.co/reference/rest-api/rooms).

`mtgSessionId`

string

The meeting session ID for this transcription.[mtgSessionId](https://docs.daily.co/reference/rest-api/logs/config#mtgSessionId).

`status`

string

Options: "t_finished","t_in_progress","t_error","t_deleted"

`isVttAvailable`

boolean

Whether the transcription has been stored in a WebVTT file. See [transcription storage](https://docs.daily.co/guides/products/transcription#enabling-domains-rooms-for-transcription-storage).

`duration`

integer

How many seconds long the transcription is, approximately.

`outParams`

object

Object representing the storage location for the transcript if `transcription_bucket` is defined.

`s3key`

string

`bucket`

string

`region`

string

`error`

string

If `status` is `t_error`, this provide the description of the error, otherwise `null`.

* * *

Previous

[Next](/reference/rest-api/transcript/list-transcript)
