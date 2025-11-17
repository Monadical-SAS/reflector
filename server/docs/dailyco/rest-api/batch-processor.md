# Source: https://docs.daily.co/reference/rest-api/batch-processor

#

Batch Processor

[Pay-as-you-go](https://www.daily.co/pricing)

## Overview

The Batch Processor is an API that performs post-processing jobs on your call media.

It accepts a recording ID from a Daily meeting or a URL to a video/audio file (e.g. mp4, mp3) and can produce a transcript of the audio, or a summary of the transcript generated from the audio.

For a complete list and description of each endpoint, refer to the [Batch Processor API reference](/reference/rest-api/batch-processor/reference).

## Types of jobs

There are few predefined post-processing jobs that the batch processor can perform from the audio of a media file:

  1. Generate a transcript
  2. Generate a summary



### Post-call transcripts

The batch processor can generate transcripts from the audio of a media file. The transcription is powered by Deepgram.

#### Example transcripts

Transcripts are formatted as `txt`, `srt`, `vtt`, and `json`.

Text:


    1

    Speaker 0: Good afternoon. My name is Anass Ali. I'm one of the final year medical students. Before we start, can I check your name and age

    2




    3

    Speaker 1: Yeah? It's, Zaines sand I'm fifty five years old.

    4




    5

    Speaker 0: And how would you like me to address you today?

    6




    7

    Speaker 1: Zaines is fine. It's

    8




    9

    Speaker 0: a pleasure to meet you, Zaines. I've just been asked by one of the doctors just to have a conversation with you really, but was brought you into hospital. Anything we discussed remain confidential within the medical team as well. Are you happy to go ahead?

    10




SRT:


    1

    1

    2

    00:00:09,975 --> 00:00:34,350

    3

    Good afternoon. My name is Anass Ali. I'm one of the final year medical students. Before we start, can I check your name and age Yeah? It's, Zaines sand I'm fifty five years old. And how would you like me to address you today? Zaines is fine. It's a pleasure to meet you, Zaines. I've just been asked by one of the doctors just to have a conversation with you really, but was brought you into hospital. Anything we discussed remain confidential within the medical team as well. Are you happy to go ahead? Yeah. Absolutely. Okay. Great. So tell me a bit about what's been going on.

    4




    5

    2

    6

    00:00:35,129 --> 00:00:38,270

    7

    Just this morning as I was leaving my house, but in the morning,

    8




    9

    3

    10

    00:00:38,875 --> 00:00:41,054

    11

    I experienced some pretty bad chest pain.

    12




VTT:


    1

    WEBVTT

    2




    3

    NOTE

    4

    Transcription provided by Deepgram

    5

    Request Id: 5534e5b9-4779-43d0-9428-1bca5976ce79

    6

    Created: 2023-09-12T07:18:26.162Z

    7

    Duration: 579.5469

    8

    Channels: 1

    9




    10

    1

    11

    00:00:09.975 --> 00:00:34.350

    12

    - Good afternoon. My name is Anass Ali. I'm one of the final year medical students. Before we start, can I check your name and age Yeah? It's, Zaines sand I'm fifty five years old. And how would you like me to address you today? Zaines is fine. It's a pleasure to meet you, Zaines. I've just been asked by one of the doctors just to have a conversation with you really, but was brought you into hospital. Anything we discussed remain confidential within the medical team as well. Are you happy to go ahead? Yeah. Absolutely. Okay. Great. So tell me a bit about what's been going on.

    13




    14

    2

    15

    00:00:35.129 --> 00:00:38.270

    16

    - Just this morning as I was leaving my house, but in the morning,

    17




JSON:

Copy to clipboard

### Post-call summaries

The batch processor can generate summaries from the audio of a media file.

#### Example summary

The summary is written as a `text` file. An example file looks like this (this is fake data):


    1

    Medical student Anass Ali interviews a 55-year-old patient named Zaines who was admitted to the hospital after experiencing severe chest pain. Zaines describes the pain as sudden, lasting for 40 minutes, and felt like pressure on his chest. The pain also radiated down his arm and up his neck. He rates the pain as an 8 or 9 out of 10. Zaines is worried that he might be having a heart attack, as his father had a similar experience when he was 65. He also reveals that he has high blood pressure and high cholesterol, for which he takes Ramipril and a statin, respectively. Zaines has been a smoker for 25 years and drinks alcohol on the weekends. The medical team plans to discuss Zaines' symptoms and conduct further examinations and investigations.

    2




## Feature configuration

These configuration options are optional [domain properties](/reference/rest-api/your-domain/set-domain-config). They affect every batch processing job on a Daily domain.

By default, batch processor outputs are stored with Daily's HIPAA-compliant storage.

Property Name| Type| Description| Default
---|---|---|---
`batch_processor_bucket`| `object`| Defines a custom S3 bucket where the batch processor will write its output to.| `null` (output stored at Daily)

This is the same style configuration as setting up your own [custom S3 storage](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket) for recordings. Please note: if `recordings_bucket` property was set on either the domain or room configuration when a recording was made, then when passing in the resulting recording id to a batch processor POST request, the _domain_ configuration for `recordings_bucket` _must match_ the recording configuration.

Copy to clipboard

## API reference

For a complete list and description of each endpoint, refer to the [Batch Processor API reference](reference/batch-processor/reference).
