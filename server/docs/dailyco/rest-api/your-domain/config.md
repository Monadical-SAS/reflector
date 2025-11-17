# Source: https://docs.daily.co/reference/rest-api/your-domain/config

# Configuration

`enable_advanced_chat`

boolean

Property that gives end users a richer chat experience. This includes:

  * Emoji reactions to chat messages
  * Emoji picker in the chat input form
  * Ability to send a Giphy chat message



⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: false

`enable_people_ui`

boolean

Determines if [Daily Prebuilt](/guides/products/prebuilt) displays the People UI. When set to true, a People button in the call tray reveals a People tab in the call sidebar. The tab lists all participants, and next to each name indicates audio status and an option to pin the participant. When `enable_people_ui` is set to false, the button and tab are hidden.

⚠️ Has no effect on custom calls built on the Daily [call object](/guides/products/call-object).

Default: true

`enable_pip_ui`

boolean

Sets whether rooms for this domain can use [Daily Prebuilt](https://www.daily.co/prebuilt)'s Picture in Picture controls. When set to `true`, an additional button will be available in Daily Prebuilt's UI to toggle the Picture in Picture feature.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: false

`enable_emoji_reactions`

boolean

Determines if [Daily Prebuilt](https://www.daily.co/prebuilt) displays the Emoji Reactions UI. When set to `true`, a Reactions button appears in the call tray. This button allows users to select and send a reaction into the call. When set to `false`, the Reactions button is hidden and the feature is disabled.

Usage: This feature is a good fit for meetings when a host or presenter would benefit from receiving nonverbal cues from the audience. It's also great to keep meetings fun.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: false

`enable_hand_raising`

boolean

Sets whether the participants in the room can use [Daily Prebuilt](https://www.daily.co/prebuilt)'s hand raising controls. When set to `true`, an additional button will be available in Daily Prebuilt's UI to toggle a hand raise.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: false

`enable_prejoin_ui`

boolean

Determines whether participants enter a waiting room with a camera, mic, and browser check before joining a call in any room under this domain.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_prejoin_ui`.

Default: true

`enable_breakout_rooms`

boolean

Sets whether rooms for this domain have [Daily Prebuilt](https://www.daily.co/prebuilt)’s breakout rooms feature enabled. When set to `true`, an owner in a Prebuilt call can create breakout rooms to divide participants into smaller, private groups.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_breakout_rooms`.

⚠️ This property is in beta.

Default: false

`enable_live_captions_ui`

boolean

Sets whether participants in a room see a closed captions button in their Daily Prebuilt call tray. When the closed caption button is clicked, closed captions are displayed locally.

When set to `true`, a closed captions button appears in the call tray. When set to `false`, the closed captions button is hidden from the call tray.

Note: Transcription must be enabled for the room or users must have permission to start transcription for this feature to be enabled. View the [transcription guide](/guides/products/transcription) for more details.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_live_captions_ui`.

Default: false

`enable_network_ui`

boolean

Determines whether the network button, and the network panel it reveals on click, appears across all rooms belonging to this domain.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_network_ui`.

Default: false

`enable_noise_cancellation_ui`

boolean

Determines whether Daily Prebuilt displays noise cancellation controls. When set to `true`, a participant can enable microphone noise cancellation during a Daily Prebuilt call. ⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object. To learn more about adding noise cancellation to a custom application, see the [`updateInputSettings()` docs](/reference/daily-js/instance-methods/update-input-settings).

Default: true

`enable_video_processing_ui`

boolean

Determines whether Daily Prebuilt displays background blur controls. When set to `true`, a participant can enable blur during a Daily Prebuilt call.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: true

`hide_daily_branding`

boolean

[Pay-as-you-go](https://www.daily.co/pricing)

Whether "Powered by Daily" displays in the in-call UI.

Default: false

`redirect_on_meeting_exit`

string

(For meetings that open in a separate browser tab.) When a user clicks on the in-call menu bar's "leave meeting" button, the browser loads this URL. A query string that includes a parameter of the form `recent-call=<domain>/<room>` is appended to the URL. On mobile, you can redirect to a deep link to bring a user back into your app.

`hipaa`

boolean

[Paid add-on](https://www.daily.co/pricing)

Email us at help@daily.co to turn on HIPAA. Learn more about [our HIPAA compliance](https://www.daily.co/hipaa-compliance).

Default: false

`intercom_auto_record`

boolean

Whether to automatically start recording when an Intercom support agent joins an Intercom-created call. Please see our [Intercom Messenger App page](https://www.daily.co/intercom) for more information.

⚠️This method is read-only; please contact us if you'd like to enable intercom call auto-recording.

`lang`

string

The default language for the video call UI, for all calls.

If you set the language at this domain level, you can still override the setting for specific rooms in [a room's configuration properties](/reference/rest-api/rooms/config), or for a specific participant in a [meeting token](/reference/rest-api/meeting-tokens/config).

You can also set the language dynamically using the front-end library [setDailyLang() method](/reference/daily-js/instance-methods/set-daily-lang).

`*` Norwegian `"no"` and Russian `"ru"` are only available in the new Daily Prebuilt.

Options: "da","de","en","es","fi","fr","it","jp","ka","nl","no","pt","pt-BR","pl","ru","sv","tr","user"

Default: en

`meeting_join_hook`

string

Sets a URL that will receive a webhook when a user joins a room.

⚠️ In place of the `meeting_join_hook`, we recommend setting up a [webhook](/reference/rest-api/webhooks) and listening for the [`participant.joined`](/reference/rest-api/webhooks/events/participant-joined) event.

Default: NULL

`geo`

string

Daily uses signaling servers to manage all of the participants in a given call session. In an SFU/server mode call, the server will send and receive all audio and video from each participant. In a peer-to-peer call, each participant sends media directly to and from each other peer, but a signaling server still manages call state.

Daily runs servers in several different AWS regions to minimize latency for users around the world. The job of 'picking' a call server is handled when the first participant joins a room. The first participant's browser connects to a call server using Amazon's Route 53 DNS resolution, which chooses a server in the region closest to them.

This isn't always optimal. For example, if one person joins in London, and then ten more people join from Cape Town, the call will still be hosted out of `eu-west-2` . The majority of the participants will have higher latency to the server than if one of them had joined first and the call was being hosted in `af-south-1`. In cases like this, you may want to configure your domain (or a specific room) to always choose a call server in a specific AWS region.

Available regions:

  * `"af-south-1"` (Cape Town)
  * `"ap-northeast-2"` (Seoul)
  * `"ap-southeast-1"` (Singapore)
  * `"ap-southeast-2"` (Sydney)
  * `"ap-south-1"` (Mumbai)
  * `"eu-central-1"` (Frankfurt)
  * `"eu-west-2"` (London)
  * `"sa-east-1"` (São Paulo)
  * `"us-east-1"` (N. Virginia)
  * `"us-west-2"` (Oregon)



Default: NULL

`rtmp_geo`

string

Used to select the region where an RTMP stream should originate. In cases where RTMP streaming services aren't available in the desired region, we'll attempt to fall back to the default region based on the SFU being used for the meeting.

Available regions:

  * `"us-west-2"` (Oregon)
  * `"eu-central-1"` (Frankfurt)
  * `"ap-south-1"` (Mumbai)



The default regions are grouped based on the SFU region like so:

  * RTMP region `"us-west-2"` includes SFU regions: `"us-west-2"`, `"us-east-1"`, `"sa-east-1"`
  * RTMP region `"eu-central-1"` includes SFU regions: `"eu-central-1"`, `"eu-west-2"`, `"af-south-1"`
  * RTMP region `"ap-south-1"` includes SFU regions: `"ap-southeast-1"`, `"ap-southeast-2"`, `"ap-northeast-2"`, `"ap-south-1"`



Default: The closest available region to the SFU region used by the meeting.

`disable_rtmp_geo_fallback`

boolean

Disable the fall back behavior of rtmp_geo. When rtmp_geo is set, we first try to connect to a media server in desired region. If a media server is not available in the desired region, we fall back to default region based on SFU's region. This property disables this automatic fall back. When this property is set, we will trigger a recording/streaming error event when media worker is unavailable. Also, the client should retry recording/streaming.

Default: false

`enable_terse_logging`

boolean

Reduces the volume of log messages. This feature should be enabled when there are more than 200 participants in a meeting to help improve performance.

See our [guides for supporting large experiences](/guides/scaling-calls) for additional instruction.

Default: false

`enable_transcription_storage`

boolean

Live transcriptions generated can be saved as WebVTT. This flag controls if transcription started with [`startTranscription()`](/reference/daily-js/instance-methods/start-transcription) should be saved or not.

Default: false

`transcription_bucket`

object

Configures an S3 bucket in which to store transcriptions. See the [S3 bucket guide](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket) for more information.

`bucket_name`

string

The name of the Amazon S3 bucket to use for transcription storage.

`bucket_region`

string

The region which the specified S3 bucket is located in.

`assume_role_arn`

string

The Amazon Resource Name (ARN) of the role Daily should assume when storing the transcription in the specified bucket.

`allow_api_access`

boolean

Whether the transcription should be accessible using Daily's API.

`recordings_template`

string

Cloud recordings are stored in either Daily's S3 bucket or the customer's own S3 bucket. By default recordings are stored as `{domain_name}/{room_name}/{epoch_time}`. Sometimes, the use case may call for custom recording file names to be used (for example, if you'd like to enforce the presence of the .mp4 extension in the file name).

`recordings_template` is made up of a replacement string with prefixes, suffixes, or both. The currently supported replacements are:

  * `epoch_time`: The epoch time in milliseconds (mandatory)
  * `domain_name`: Your Daily domain (optional)
  * `room_name`: The name of the room which is getting recorded (optional)
  * `mtg_session_id`: The ID of the meeting session which is getting recorded (optional)
  * `instance_id`: The instance ID of the recording (optional)
  * `recording_id`: The recording ID of the recording (optional)



The restrictions for defining a recording template are as follows:

  * The `epoch_time` tag is mandatory to ensure the recording file name is unique under all conditions
  * The maximum size of the template is 1024 characters
  * Each replacement parameter should be placed within a curly bracket (e.g., `{domain_name}`)
  * Only alphanumeric characters `(0-9, A-Z, a-z)` and `.`, `/`, `-`, `_` are valid within the template
  * `.mp4` is the only valid extension



Examples

  * Example domain: "myDomain"
  * Example room: "myRoom"



Example 1:

  * Template: `myprefix-{domain_name}-{epoch_time}.mp4`
  * Resulting file name: `myprefix-myDomain-1675842936274.mp4`



Example 2:

  * Template: `{room_name}/{instance_id}/{epoch_time}`
  * Resulting room name: `myRoom/d529cd2f-fbcc-4fb7-b2c0-c4995b1162b6/1675842936274`



Default: {domain_name}/{room_name}/{epoch_time}.

`transcription_template`

string

transcriptions can be stored in either Daily's S3 bucket or the customer's own S3 bucket. By default transcriptions are stored as `{domain_name}/{room_name}/{epoch_time}.vtt`. Sometimes, the use case may call for custom file path to be used (for example, if you'd like to map stored transcription to mtgSessionId).

`transcription_template` is made up of a replacement string with prefixes, suffixes, or both. The currently supported replacements are:

  * `epoch_time`: The epoch time in seconds (mandatory)
  * `domain_name`: Your Daily domain (optional)
  * `room_name`: The name of the room which is getting transcribed (optional)
  * `mtg_session_id`: The ID of the meeting session which is getting transcribed (optional)
  * `instance_id`: The instance ID of the transcription (optional)
  * `transcript_id`: The transcript ID of the transcription (optional)



The restrictions for defining a transcription template are as follows:

  * The `epoch_time` tag is mandatory to ensure the transcription file name is unique under all conditions
  * The maximum size of the template is 1024 characters
  * Each replacement parameter should be placed within a curly bracket (e.g., `{domain_name}`)
  * Only alphanumeric characters `(0-9, A-Z, a-z)` and `.`, `/`, `-`, `_` are valid within the template



Examples

  * Example domain: "myDomain"
  * Example room: "myRoom"



Example 1:

  * Template: `myprefix-{domain_name}-{epoch_time}.mp4`
  * Resulting file name: `myprefix-myDomain-1675842936274.mp4`



Example 2:

  * Template: `{room_name}/{instance_id}/{epoch_time}`
  * Resulting room name: `myRoom/d529cd2f-fbcc-4fb7-b2c0-c4995b1162b6/1675842936274`



Default: {domain_name}/{room_name}/{epoch_time}.vtt.

`enable_mesh_sfu`

boolean

Configures a room to use multiple SFUs for a call's media. This feature enables calls to scale to large sizes and to reduce latency between participants. It is recommended specifically for interactive live streaming.

See our [guide for interactive live streaming](/guides/scaling-calls/interactive-live-streaming-rtmp-output#daily-prebuilt-configurations-to-support-100-000-participants) for additional instruction.

`sfu_switchover`

number

Dictates the participant count after which room topology automatically switches from Peer-to-Peer (P2P) to Selective Forwarding Unit (SFU) mode, or vice versa.

For example, if `sfu_switchover` is set to `2` and the current network topology is P2P, the topology will switch to SFU mode when the _third_ participant joins the call. If the current topology is SFU, it will switch to P2P mode when the participant count decreases from `2` to `1`.

We recommend specifying an integer value for this property except for cases where you would like the room to switch to SFU mode as soon as the first participant joins. In this case, set `sfu_switchover` to `0.5`.

See our [guide about video call architecture](/guides/architecture-and-monitoring/intro-to-video-arch#the-architecture-of-a-room-p2p-vs-sfu-calls) for additional information.

Default: 0.5

`enable_adaptive_simulcast`

boolean

Configures a domain or room to use [Daily Adaptive Bitrate](/guides/building-additional-features/daily-adaptive-bitrate). When enabled, along with configuring the client to [`allowAdaptiveLayers`](/reference/daily-js/instance-methods/update-send-settings#sendsettings), the Daily client will continually adapt send settings to the current network conditions. `allowAdaptiveLayers` is `true` by default; if you haven't modified that setting, then setting `enable_adaptive_simulcast` to `true` will enable Daily Adaptive Bitrate for 1:1 calls.

Default: true

`enforce_unique_user_ids`

boolean

Configures a domain or room to disallow multiple participants from having the same `user_id`. This feature can be enabled to prevent users from "sharing" meeting tokens. When enabled, a participant joining or reconnecting to a meeting will cause existing participants with the same user_id to be ejected.

Default: false

`recordings_bucket`

object

Configures an S3 bucket in which to store recordings. See the [S3 bucket guide](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket) for more information.

Properties:

`bucket_name`

string

The name of the Amazon S3 bucket to use for recording storage.

`bucket_region`

string

The region which the specified S3 bucket is located in.

`assume_role_arn`

string

The Amazon Resource Name (ARN) of the role Daily should assume when storing the recording in the specified bucket.

`allow_api_access`

boolean

Controls whether the recording will be accessible using Daily's API.

`allow_streaming_from_bucket`

boolean

Specifies which [`Content-Disposition`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition) response header the recording link retrieved from the [access-link](/reference/rest-api/recordings/get-recording-link) REST API endpoint will have. If `allow_streaming_from_bucket` is `false`, the header will be `Content-Dispostion: attachment`. If `allow_streaming_from_bucket` is `true`, the header will be `Content-Disposition: inline`. To play the recording link directly in the browser or embed it in a video player, set this property to `true`.

Default: false

`permissions`

object

Specifies the initial default permissions for a non-[meeting-owner](/guides/configurations-and-settings/controlling-who-joins-a-meeting#meeting-owner-privileges) participant joining a call.

Each permission (i.e. each of the properties listed below) can be configured in the meeting token, the room, and/or the domain, in decreasing order of precedence.

Participant admins (those with the `'participants'` value in their `canAdmin` permission) can also change participants' permissions on the fly during a call using [`updateParticipant()`](/reference/daily-js/instance-methods/update-participant#permissions) or [`updateParticipants()`](/reference/daily-js/instance-methods/update-participants).

`hasPresence`

boolean

Whether the participant appears as "present" in the call, i.e. whether they appear in [`participants()`](/reference/daily-js/instance-methods/participants#main).

`canSend`

boolean | array

Which types of media a participant should be permitted to send.

Can be:

  * An Array containing any of `'video'`, `'audio'`, `'screenVideo'`, and `'screenAudio'`
  * `true` (meaning "all")
  * `false` (meaning "none")



`canReceive`

object

Which media the participant should be permitted to receive.

[See here for `canReceive` object format](/reference/daily-js/instance-methods/participants#permissionscanreceive-properties).

`canAdmin`

boolean | array

Which admin tasks a participant is permitted to do.

Can be:

  * An array containing any of `'participants'`, `'streaming'`, or `'transcription'`
  * `true` (meaning "all")
  * `false` (meaning "none")



Default: { canSend: true, canReceive: { base: true }, hasPresence: true, canAdmin: false }

`batch_processor_bucket`

object

Defines a custom S3 bucket where the batch processor will write its output

`enable_opus_fec`

boolean

Enables the use of Opus in-band FEC (Forward Error Correction) when encoding audio to send, where possible. This can make audio quality more resilient to packet loss.

`pinless_dialin`

array

[Pay-as-you-go](https://www.daily.co/pricing)

[SIP Interconnect and Pinless Dialin](/guides/products/dial-in-dial-out/dialin-pinless#provisioning-sip-interconnect-and-pinless-dialin-workflow),i.e., without entering a PIN code when dialling a phone number or directly calling a Daily SIP Interconnect address. In this case you dont need a SIP address associated to a particular Daily Room.

When a call comes in to this phone number or to the sip interconnect address, it will trigger a webhook, where you'll need to create the Daily room and forward the call to the `sipUri` assocaited to the newly created room.

The Pinless Dialin only works with purchased phone numbers, because the call is not intended for a particular Daily room. Read more details on our [dosc-site](/guides/products/dial-in-dial-out/dialin-pinless).

`pin_dialin`

array

[Pay-as-you-go](https://www.daily.co/pricing)

Dialin with a [PIN code](/guides/products/dial-in-dial-out/dialin-pin). This works with both the Global phone numbers and any number that you purchased. When a call comes into one of the phone numbers, the dialer must enter the PIN code. If the code is correct, the user will be connected to the Daily Room. Otherwise the incoming call will be disconnected if an incorrect PIN code is entered.

* * *

Previous

[Next](/reference/rest-api/your-domain/get-domain-config)
