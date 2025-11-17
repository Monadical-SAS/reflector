# Source: https://docs.daily.co/reference/rest-api/recordings/config

# Configuration

`id`

string

A unique, opaque ID for this object. You can use this ID in API calls, and in paginated list operations.

`room_name`

string

The name of the [room](https://docs.daily.co/reference/rest-api/rooms).

`start_ts`

integer

When the recording started. This is a unix timestamp (seconds since the epoch).

`status`

string

Options: "finished","in-progress","canceled"

`max_participants`

integer

The maximum number of participants that were ever in this room together during the meeting session that was recorded.

`duration`

integer

How many seconds long the recording is, approximately. This property is not returned for recordings that are in-progress.

`share_token`

string

Deprecated.

`s3key`

string

The S3 Key associated with this recording.

`mtgSessionId`

string

The meeting session ID for this recording.

`tracks`

array

If the recording is a raw-tracks recording, a tracks field will be provided. If role permissions have been removed, the tracks field may be null.

* * *

Previous

[Next](/reference/rest-api/recordings/list-recordings)
