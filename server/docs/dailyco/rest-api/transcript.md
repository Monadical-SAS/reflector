# Source: https://docs.daily.co/reference/rest-api/transcript

#

Transcription

[Pay-as-you-go](https://www.daily.co/pricing)

**Beta feature**

The transcription endpoint allows you to [retrieve the transcript](/reference/rest-api/transcript/list-transcript), [get a link to the transcript](/reference/rest-api/transcript/get-transcript-link), and [delete](/reference/rest-api/transcript/delete-transcript) transcripts with the Daily API.

Transcription is started with [`startTranscription()`](/reference/daily-js/instance-methods/start-transcription). Transcriptions can be also saved in Daily's S3 bucket or a custom S3 bucket.

## The "transcript" object

A transcription object represents a single transcription. All of the transcription configurations properties are [referenced here](/reference/rest-api/transcript/config).

Copy to clipboard

Head to our **[transcription guide](/guides/products/transcription)** for detailed information on how to transcribe a call.
