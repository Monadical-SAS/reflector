# Source: https://docs.daily.co/reference/rest-api/rooms/set-room-config

#

POST

/rooms/:room

**A`POST` request to `/rooms/:name` modifies a [room object](/reference/rest-api/rooms)'s privacy or configuration properties.**

Returns a [room object](/reference/rest-api/rooms) if the operation is successful.

In the case of an error, returns an HTTP error with information about the error in the response body.

## Path params

`name`

string

Defaults to a randomly generated string A room name can include only the uppercase and lowercase ascii letters, numbers, dash and underscore. In other words, this regexp detects an invalid room name: /[^A-Za-z0-9_-]/.

The room name cannot exceed 128 characters. You'll get an error if you try to create a room with a name that's too long.

## Body params

### `privacy`

`privacy`

string

`Determines who can access the room. `

Options: "public","private"

Default: "public"

### `properties`

`nbf`

integer

"Not before". This is a [unix timestamp](https://stackoverflow.com/questions/20822821/what-is-a-unix-timestamp-and-why-use-it) (seconds since the epoch.) Users cannot join a meeting in this room before this time.

`exp`

integer

"Expires". This is a unix timestamp (seconds since the epoch.) Users cannot join a meeting in this room after this time.

More resources:

  * [Add advanced security to video chats with the Daily API](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/)



`max_participants`

integer

[Pay-as-you-go](https://www.daily.co/pricing)

How many people are allowed in a room at the same time.

⚠️ [Contact us](https://www.daily.co/contact) if you need to set the limit above 200.

Default: 200

`enable_people_ui`

boolean

Determines if [Daily Prebuilt](/guides/products/prebuilt) displays the People UI. When set to true, a People button in the call tray reveals a People tab in the call sidebar. The tab lists all participants, and next to each name indicates audio status and an option to pin the participant. When `enable_people_ui` is set to false, the button and tab are hidden.

⚠️ Has no effect on custom calls built on the Daily [call object](/guides/products/call-object).

`enable_pip_ui`

boolean

Sets whether the room can use [Daily Prebuilt](https://www.daily.co/prebuilt)'s Picture in Picture controls. When set to `true`, an additional button will be available in Daily Prebuilt's UI to toggle the Picture in Picture feature.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

`enable_emoji_reactions`

boolean

Determines if [Daily Prebuilt](https://www.daily.co/prebuilt) displays the Emoji Reactions UI. When set to `true`, a Reactions button appears in the call tray. This button allows users to select and send a reaction into the call. When set to `false`, the Reactions button is hidden and the feature is disabled.

Usage: This feature is a good fit for meetings when a host or presenter would benefit from receiving nonverbal cues from the audience. It's also great to keep meetings fun.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

`enable_hand_raising`

boolean

Sets whether the participants in the room can use [Daily Prebuilt](https://www.daily.co/prebuilt)'s hand raising controls. When set to `true`, an additional button will be available in Daily Prebuilt's UI to toggle a hand raise.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

`enable_prejoin_ui`

boolean

Determines whether participants enter a waiting room with a camera, mic, and browser check before joining a call.

⚠️ You must be using [Daily Prebuilt](https://daily.co/prebuilt) to use `enable_prejoin_ui`.

`enable_live_captions_ui`

boolean

Sets whether participants in a room see a closed captions button in their Daily Prebuilt call tray. When the closed caption button is clicked, closed captions are displayed locally.

When set to `true`, a closed captions button appears in the call tray. When set to `false`, the closed captions button is hidden from the call tray.

Note: Transcription must be enabled for the room or users must have permission to start transcription for this feature to be enabled. View the [transcription guide](/guides/products/transcription) for more details.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_live_captions_ui`.

`enable_network_ui`

boolean

Determines whether the network button, and the network panel it reveals on click, appears in this room.

⚠️ You must be using [Daily Prebuilt](https://daily.co/prebuilt) to use `enable_network_ui`.

`enable_noise_cancellation_ui`

boolean

Determines whether Daily Prebuilt displays noise cancellation controls. When set to `true`, a participant can enable microphone noise cancellation during a Daily Prebuilt call. ⚠️ This flag only applies to [Daily Prebuilt](https://daily.co/prebuilt). It has no effect when building custom video applications with the Daily call object. To learn more about adding noise cancellation to a custom application, see the [`updateInputSettings()` docs](/reference/daily-js/instance-methods/update-input-settings).

`enable_breakout_rooms`

boolean

Sets whether [Daily Prebuilt](https://www.daily.co/prebuilt)’s breakout rooms feature is enabled. When set to `true`, an owner in a Prebuilt call can create breakout rooms to divide participants into smaller, private groups.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_breakout_rooms`.

⚠️ This property is in beta.

`enable_knocking`

boolean

Turns on a lobby experience for private rooms. A participant without a corresponding [meeting token](/reference/rest-api/meeting-tokens/config) can request to be admitted to the meeting with a "knock", and wait for the meeting owner to admit them.

`enable_screenshare`

boolean

Sets whether users in a room can screen share during a session. This property cannot be changed after a session starts. For dynamic control over permissions, use the [`updateParticipant()`](/reference/daily-js/instance-methods/update-participant#permissions) method to control user permissions.

Default: true

`enable_video_processing_ui`

boolean

Determines whether Daily Prebuilt displays background blur controls. When set to `true`, a participant can enable blur during a Daily Prebuilt call.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: true

`enable_chat`

boolean

This property is one of [multiple ways to add chat to Daily video calls](https://www.daily.co/blog/three-ways-to-add-chat-to-your-video-calls-with-the-daily-api/).

Default: false

`enable_shared_chat_history`

boolean

When enabled, newly joined participants in Prebuilt calls will request chat history from remote peers, in order to view chat messages from before they joined.

Default: true

`start_video_off`

boolean

Disable the default behavior of automatically turning on a participant's camera on a direct `join()` (i.e. without `startCamera()` first).

Default: false

`start_audio_off`

boolean

Disable the default behavior of automatically turning on a participant's microphone on a direct `join()` (i.e. without `startCamera()` first).

Default: false

`owner_only_broadcast`

boolean

In Daily Prebuilt, only the meeting owners will be able to turn on camera, unmute mic, and share screen.

See [setting up calls](https://docs.daily.co/docs/setting-up-calls).

Default: false

`enable_recording`

string

Jump to [recording docs](/reference/rest-api/recordings).

Options: "cloud","local","raw-tracks","<not set>"

Default: <not set>

`eject_at_room_exp`

boolean

If there's a meeting going on at room `exp` time, end the meeting by kicking everyone out. This behavior can be overridden by setting `eject` properties of a [meeting token](/reference/rest-api/meeting-tokens).

Default: false

`eject_after_elapsed`

integer

Eject a meeting participant this many seconds after the participant joins the meeting. You can use this is a default length limit to prevent long meetings. This can be overridden by setting `eject` properties of a [meeting token](/reference/rest-api/meeting-tokens).

`enable_advanced_chat`

boolean

Property that gives end users a richer chat experience. This includes:

  * Emoji reactions to chat messages
  * Emoji picker in the chat input form
  * Ability to send a Giphy chat message



⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

Default: false

`enable_hidden_participants`

boolean

When enabled, non-owner users join a meeting with a hidden presence, meaning they won't appear as a named participant in the meeting and have no [participant events](https://docs.daily.co/reference/daily-js/events/participant-events) associated to them. Additionally, these participants can _only_ receive media tracks from owner participants.

Hidden participants can be tracked using the [`participantCounts()`](/reference/daily-js/instance-methods/participant-counts) method. Hidden participants do _not_ have entries in the [`participants()`](/reference/daily-js/instance-methods/participants) method return value.

When used with [Daily Prebuilt](/guides/products/prebuilt), hidden participants are included in the participant count available in the UI; however, are _not_ included in the People panel and can only read chat messages.

This property should be used to support hosting large meetings. See our [guide on interactive live streaming](/guides/scaling-calls/interactive-live-streaming-rtmp-output#interactive-live-streaming-up-to-100-000-participants) for additional instruction.

Default: false

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

`enable_multiparty_adaptive_simulcast`

boolean

Configures a domain or room to use [Daily Adaptive Bitrate](/guides/building-additional-features/daily-adaptive-bitrate). When enabled, along with configuring the client to [`allowAdaptiveLayers`](/reference/daily-js/instance-methods/update-send-settings#sendsettings), the Daily client will continually adapt send settings to the current network conditions. `allowAdaptiveLayers` is `true` by default; if you haven't modified that setting, then setting `enable_multiparty_adaptive_simulcast` to `true` will enable Daily Adaptive Bitrate for multi-party calls. To use this feature, `enable_adaptive_simulcast` must also be set to `true`.

Default: false

`enforce_unique_user_ids`

boolean

Configures a domain or room to disallow multiple participants from having the same `user_id`. This feature can be enabled to prevent users from "sharing" meeting tokens. When enabled, a participant joining or reconnecting to a meeting will cause existing participants with the same user_id to be ejected.

Default: false

`experimental_optimize_large_calls`

boolean

Enables Daily Prebuilt to support group calls of up to 1,000 participants and [owner only broadcast](/reference/rest-api/rooms/config#owner_only_broadcast) calls of up to 100K participants.

When set to true, Daily Prebuilt will:

  * Automatically mute the local user on joining
  * Update grid view to show a maximum of 12 users in the grid at a time
  * Allow only 16 users to be unmuted at the same time. When more than 16 users are unmuted, the oldest active speaker will be automatically muted.



See our [guide on large real-time calls](/guides/scaling-calls/large-real-time-calls) for additional instruction.

⚠️ This flag only applies to Daily Prebuilt. It has no effect when building custom video applications with the Daily call object.

`lang`

string

The default language of the [Daily prebuilt video call UI](/guides/products/prebuilt#daily-prebuilt-ui), for this room.

Setting the language at the room level will override any domain-level language settings you have.

Read more about [changing prebuilt UI language settings](https://help.daily.co/en/articles/4579930-changing-the-language-setting-of-the-prebuilt-ui).

`*` Norwegian `"no"` and Russian `"ru"` are only available in the new Daily Prebuilt.

Options: "da","de","en","es","fi","fr","it","jp","ka","nl","no","pt","pt-BR","pl","ru","sv","tr","user"

Default: en

`meeting_join_hook`

string

Sets a URL that will receive a webhook when a user joins a room. Default is NULL. Character limit for webhook URL is 255.

⚠️ In place of the `meeting_join_hook`, we recommend setting up a [webhook](/reference/rest-api/webhooks) and listening for the [`participant.joined`](/reference/rest-api/webhooks/events/participant-joined) event.

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

`enable_terse_logging`

boolean

Reduces the volume of log messages. This feature should be enabled when there are more than 200 participants in a meeting to help improve performance.

See our [guides for supporting large experiences](/guides/scaling-calls) for additional instruction.

Default: false

`auto_transcription_settings`

object

[Pay-as-you-go](https://www.daily.co/pricing)

Options to use when `auto_start_transcription` is true. See [`startTranscription()`](/reference/daily-js/instance-methods/start-transcription) for available options.

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

`enable_dialout`

boolean

Allow [dialout](/reference/daily-js/instance-methods/start-dial-out) API from the room.

Default: false

`dialout_config`

object

Allow configuring [dialout](/reference/daily-js/instance-methods/start-dial-out) behaviour.

`allow_room_start`

boolean

Setting this to true allows starting the room and initiating the dial-out even though there is no user present in the room. By default, initiating a [dial-out](/reference/rest-api/rooms/dialout/start) via the REST API fails when the corresponding room is empty (without any participant).

Default: false

`dialout_geo`

string

The region where SFU is selected to start the room. default is taken from [`room geo`](/reference/rest-api/rooms/config#geo) else from [`domain geo`](/reference/rest-api/your-domain/config#geo) and if both are not defined `us-west-2` is take as default.

`max_idle_timeout_sec`

number

Number of seconds where dialout user can be alone in the room. dialout user can start the room and can remain in the room alone waiting for other participant for this duration, also when all the web users leave the room, room is automatically closed, this property allows dialout user to remain in room after all web users leave the room.

Default: 0

`streaming_endpoints`

array

An array of stream endpoint configuration objects, which allows configurations to be pre-defined without having to pass them into [`startLiveStreaming()`](/reference/daily-js/instance-methods/start-live-streaming) at runtime. For example, an RTMP endpoint can be set up for YouTube as a `streaming_endpoints` configuration along with another configuration for HLS storage.

HLS output can only be stored on a customer's S3, not in Daily's storage infrastructure. The stream configuration defines which S3 bucket to store the HLS output. (See the [S3 bucket guide](/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket) for more information.)

Example:

Copy to clipboard

To reset the `streaming_endpoints` property, pass `null` instead of an array.

When calling `startLiveStreaming()`, the pre-defined `streaming_endpoints` `name` can be used:

Copy to clipboard

Properties:

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



Default: <not set>

## Example requests

### Change a room's privacy

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

### Change a room's `max_participants` property

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

### Change a room's `max_participants` property back to default

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/rooms/get-room-presence)

[Next](/reference/rest-api/rooms/delete-room)
