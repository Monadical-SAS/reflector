# Source: https://docs.daily.co/reference/rest-api/rooms/transcription/start

#

POST

/rooms/:name/transcription/start

Starts a transcription with given parameters.

[Attach a credit card](https://dashboard.daily.co) to your Daily account to start using this feature.

## Path params

`name`

string

The name of the room.

## Body params

`language`

string

See Deepgram's documentation for [`language`](https://developers.deepgram.com/docs/language)

`model`

string

See Deepgram's documentation for [`model`](https://developers.deepgram.com/docs/model)

`tier`

string

This field is deprecated, use `model` instead

`profanity_filter`

boolean

See Deepgram's documentation for [`profanity filter`](https://developers.deepgram.com/docs/profanity-filter)

`punctuate`

boolean

See Deepgram's documentation for [`punctuate`](https://developers.deepgram.com/docs/punctuation)

`endpointing`

number | boolean

See Deepgram's documentation for [`endpointing`](https://developers.deepgram.com/docs/endpointing)

`redact`

boolean | array

See Deepgram's documentation for [`redact`](https://developers.deepgram.com/docs/redaction)

`extra`

object

Specify any Deepgram parameters. See Deepgram's documentation for [available streaming options](https://developers.deepgram.com/docs/features-overview)

`includeRawResponse`

boolean

Whether Deepgram's raw response should be included in all transcription messages

`instanceId`

string

A developer provided ID of an instance, which is used for multi-instance transcription.

`participants`

array

A list of participant IDs to be transcribed. Only the participant IDs included in this array will be processed.

## Example requests

**Default**

**Set language**

**Select model**

**Apply profanity filter**

**Redact credit card information**

Copy to clipboard

## Example responses

**200 OK**

**404 Room is not hosting a call**

**400 Stream in progress**

**400 Room not in SFU mode**

**400 Call closed before command could be delivered**

**400 Deepgram API key invalid**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/rooms/transcription/update)
