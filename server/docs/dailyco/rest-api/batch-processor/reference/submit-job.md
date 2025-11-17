# Source: https://docs.daily.co/reference/rest-api/batch-processor/reference/submit-job

#

Submit a job

[Pay-as-you-go](https://www.daily.co/pricing)

## POST /batch-processor

This endpoint is used to submit jobs to the batch processor.

A job request includes three components: a preset (`preset`), an input configuration (`inParams`), an output configuration (`outParams`).

The `preset` defines the type of job to run. This is a required attribute and available presets are: `transcript`, `summarize`.

The `inParams` defines where the inputs for the job are coming from. An existing `recordingId` or a URL to a video/audio file are the two possible configurations.

The `outParams` defines how the outputs for the job are configured like the filename of the output.

Depending on the preset type, an optional `transformParams` object may contain configuration that describes the transformation applied to the data. Currently only the `transcript` preset supports these transform configuration options.

### Request Template (`json`)

Copy to clipboard

### Top-level configuration

Attribute Name| Type| Description| Default| Example| Required?
---|---|---|---|---|---
`preset`| `string`| The type of job to run| `null`| [transcript, summarize]| Yes
`inParams`| `object`| The input configuration| `null`| `{...}`| Yes
`outParams`| `object`| The output configuration| `null`| `{...}`| Yes
`transformParams`| `object`| The output configuration| `null`| `{...}`| No

### Input configuration (`inParams`)

Attribute Name| Type| Description| Default| Example| Required?
---|---|---|---|---|---
`sourceType`| `string`| The type of the input media: [uri, recordingId]| `null`| One of [uri, recordingId]| Yes
`uri`| `string`| The actual URL when using "uri" as sourceType| `null`| "https://direct-url-to/file.mp4"| When using `uri` as `sourceType`
`recordingId`| `string`| The recording ID when using `recordingId` as sourceType| `null`| "uuiasdfe-8ba2-4ee6-bd15-003a92c18245"| When using `recordingId` as `sourceType`
`language`| `string`| The BCP-47 language-tag of spoken the audio for the transcription| `en`| "fr"| No

 _Note:_ `language` in `inParams` is only supported for the `transcript` preset. Additional options are available for transcriptions, see below.

### Transform configuration (`transformParams`)

Attribute Name| Type| Description| Default| Example| Required?
---|---|---|---|---|---
`transcript`| `object`| Configuration specific to transcription| `null`| `{...}`| No

### Transcription configuration (`transformParams.transcript`)

The following parameters can be passed in the `transformParams.transcript` object. None of the parameters are required. See the documentation for each parameter for more information on their default values.

Note that you can include more parameters using the `extra` object.

If you pass a value for `language` both using `inParams` and this configuration object, the value provided here will be used.

Name| Type| Description
---|---|---
`language`| `string`| See Deepgram's documentation for [`language`](https://developers.deepgram.com/docs/language)
`model`| `string`| See Deepgram's documentation for [`model`](https://developers.deepgram.com/docs/model)
`tier`| `string`| This field is deprecated, use `model` instead
`profanity_filter`| `boolean`| See Deepgram's documentation for [`profanity_filter`](https://developers.deepgram.com/docs/profanity-filter)
`punctuate`| `boolean`| See Deepgram's documentation for [`punctuate`](https://developers.deepgram.com/docs/punctuation)
`endpointing`| `number` or `boolean`| See Deepgram's documentation for [`endpointing`](https://developers.deepgram.com/docs/endpointing)
`redact`| `boolean` or `array`| See Deepgram's documentation for [`redact`](https://developers.deepgram.com/docs/redaction)
`extra`| `object`| Specify additional parameters. See Deepgram's documentation for [available streaming options](https://developers.deepgram.com/docs/features-overview)

### Language Support

The exact list of supported languages may depend on the `model` parameter in transcription configuration (see above).

In the default configuration, the supported languages using the `language` parameter are:

Language| BCP-47 tag
---|---
Danish| da
Dutch| nl
English| en
English Australia| en-AU
English UK| en-GB
English India| en-IN
English NewZealand| en-NZ
English USA| en-US
French| fr
French Canada| fr-CA
German (DE)| de
Hindi| hi
Hindi Roman| hi-Latn
Indonedian| id
Italian| it
Japanese| ja
Korean| ko
Norwegian| no
Polish| pl
Portuguese| pt
Portuguese Brazil| pt-BR
Portuguese Portugal| pt-PT
Russian| ru
Spanish| es
Spanish Latin America| es-419
Swedish| sv
Turkish| tr
Ukrainian| uk

### Output configuration (`outParams`)

Attribute Name| Type| Description| Default| Example| Required?
---|---|---|---|---|---
`s3config.s3KeyTemplate`| `string`| The filename of the output| `null`| "my-summary"| Yes
`s3config.useReplacement`| `boolean`| whether to use template replacement in s3KeyTemplate| `null`| true| No

### s3KeyReplacement

The default output path for `transcript` and `summary` jobs are `domain_name/jobId/transcript/s3Config.s3KeyTemplate` `domain_name/jobId/summary/s3Config.s3KeyTemplate` respectively.

s3KeyReplacement with useReplacement can be used to customize the S3 path of the generated output, template replacements are made up of a replacement string with prefixes, suffixes, or both. The currently supported replacements are:

epoch_time: The epoch time in seconds (optional)

domain_name: Your Daily domain (optional)

job_id: The job ID assigned to the job (optional)

The restrictions for defining a recording template are as follows:

The maximum size of the template is 1024 characters

Each replacement parameter should be placed within a curly bracket (e.g., {domain*name})

Only alphanumeric characters (0-9, A-Z, a-z) and ., /, -, * are valid within the template .mp4 is the only valid extension

Examples

Example domain: "myDomain"

Template: myprefix-{domain_name}-{epoch_time}

Resulting transcripts names:

`myprefix-myDomain-1675842936274.vtt` `myprefix-myDomain-1675842936274.json` `myprefix-myDomain-1675842936274.txt`

### Transcript example requests

**Transcript with media file**

**Transcript with recording id**

**Special Words in Transcript with media file**

Copy to clipboard

### Summary example requests

**Summary with media file**

**Summary with recording id**

**Summary with transcript**

Copy to clipboard

### Example responses

**200 OK**

**400 Bad request**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/batch-processor/reference/get-job)
