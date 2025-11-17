# Source: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token

#

POST

/meeting-tokens

**A`POST` request to `/meeting-tokens` creates a new meeting token.**

If the token is successfully created, a response body with a single field, `token`, is returned. Otherwise, an HTTP error is returned.

This is not the only way to generate a token. You can also self-sign the JWT using your API key. Read more [here](/reference/rest-api/meeting-tokens/self-signing-tokens).

## Body params

### `properties`

`room_name`

string

The room for which this token is valid. If `room_name` isn't set, the token is valid for all rooms in your domain. *You should always set `room_name` if you are using this token to control access to a meeting.

`eject_at_token_exp`

boolean

Kick this user out of the meeting at the time this meeting token expires. If either this property or `eject_after_elapsed` are set for the token, the room's `eject` properties are overridden.

_See an example in our[advanced security tutorial](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/)_.

Default: false

`eject_after_elapsed`

integer

Kick this user out of the meeting this many seconds after they join the meeting. If either this property or `eject_at_token_exp` are set for the token, the room's `eject` properties are overridden.

_See an example in our[advanced security tutorial](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/)_.

`nbf`

integer

"Not before". This is a [unix timestamp](https://stackoverflow.com/questions/20822821/what-is-a-unix-timestamp-and-why-use-it) (seconds since the epoch.) Users cannot join a meeting in with this token before this time.

`exp`

integer

"Expires". This is a unix timestamp (seconds since the epoch.) Users cannot join a meeting with this token after this time.

Daily strongly recommends adding an `exp` value to all meeting tokens. Learn more in our Daily blog post: [Add advanced security to video chats with the Daily API](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/)

`is_owner`

boolean

The user has [meeting owner privileges](https://docs.daily.co/docs/controlling-who-joins-a-meeting#meeting-owner-privileges). For example, if the room is configured for `owner_only_broadcast` and used in a Daily Prebuilt call, this user can send video, and audio, and can screenshare.

Default: false

`user_name`

string

The user's name in this meeting. The name displays in the user interface when the user is muted or has turned off the camera, and in the chat window. This username is also saved in the meeting events log (meeting events are retrievable using the [analytics](/reference/rest-api/meetings) API methods.)

`user_id`

string

The user's ID for this meeting session. During a session, this ID is retrievable in the [`participants()`](/reference/daily-js/instance-methods/participants) method and [related participant events](/reference/daily-js/events/participant-events). Either during or after a session concludes, this ID is retrievable using the [/meetings](/reference/rest-api/meetings) REST API endpoint. You can use `user_id` to map between your user database and meeting events/attendance.

For domains configured for [HIPAA compliance](/guides/privacy-and-security/hipaa), if the `user_id` value is a [UUID](https://www.ietf.org/rfc/rfc4122.txt) (for example, `f81d4fae-7dec-11d0-a765-00a0c91e6bf6`), then the UUID will be returned for the participant in the [`/meetings`](/reference/rest-api/meetings) REST API endpoint. Otherwise, the string `hipaa` will be returned in order to remove potential PHI. During a session, the provided `user_id` will always be returned through the `participants()` method and related events, regardless of the `user_id` value.

The `user_id` has a limit of 36 characters.

`enable_screenshare`

boolean

Sets whether or not the user is allowed to screen share. This setting applies for the duration of the meeting. If you're looking to dynamically control whether a user can screen share during a meeting, then use the [`permissions`](/reference/rest-api/meeting-tokens/config#permissions) token property.

Default: true

`start_video_off`

boolean

Disable the default behavior of automatically turning on a participant's camera on a direct `join()` (i.e. without `startCamera()` first).

Default: false

`start_audio_off`

boolean

Disable the default behavior of automatically turning on a participant's microphone on a direct `join()` (i.e. without `startCamera()` first).

Default: false

`enable_recording`

string

Jump to [recording docs](/reference/rest-api/recordings).

Options: "cloud","local","raw-tracks"

`enable_prejoin_ui`

boolean

Determines whether the participant using the meeting token enters a waiting room with a camera, mic, and browser check before joining a call. If this property is also set in the room or domain's configuration, the meeting token's configuration will take priority.

⚠️ You must be using [Daily Prebuilt](https://daily.co/prebuilt) to use `enable_prejoin_ui`.

`enable_live_captions_ui`

boolean

Sets whether the participant sees a closed captions button in their Daily Prebuilt call tray. When the closed caption button is clicked, closed captions are displayed locally.

When set to `true`, a closed captions button appears in the call tray. When set to `false`, the closed captions button is hidden from the call tray.

Note: Transcription must be enabled for the room or users must have permission to start transcription for this feature to be enabled. View the [transcription guide](/guides/products/transcription) for more details.

⚠️ You must be using [Daily Prebuilt](https://daily.co/blog/daily-prebuilt-video-chat) to use `enable_live_captions_ui`.

`enable_recording_ui`

boolean

Determines whether the participant using the meeting token can see the Recording button in Daily Prebuilt's UI, which can be found in the video call tray. If this value is `false`, the button will not be included in the tray. If it's `true`, the Recording button will be displayed.

This option is useful when only specific call participants should have recording permissions.

⚠️ You must be using [Daily Prebuilt](https://daily.co/prebuilt) to use `enable_recording_ui`.

`enable_terse_logging`

boolean

Reduces the volume of log messages. This feature should be enabled when there are more than 200 participants in a meeting to help improve performance.

See our [guides for supporting large experiences](/guides/scaling-calls) for additional instruction.

Default: false

`knocking`

boolean

Requires the `enable_knocking` property to be set on the room. By default, if a user joins a room with `enable_knocking` set, and with a token, they will bypass the waiting screen and join the room directly. If this property is set to `true`, the user will be required to request access, and the owner will need to accept them before they can join.

Default: false

`start_cloud_recording`

boolean

[Pay-as-you-go](https://www.daily.co/pricing)

Start cloud recording when the user joins the room. This can be used to always record and archive meetings, for example in a customer support context.

Note: This requires the `enable_recording` property of the room or token to be set to `cloud`. If you want to automatically record calls with other recording modes, use `callObject.startRecording()` after `await callObject.join()` in your code.

Default: false

`start_cloud_recording_opts`

object

[Pay-as-you-go](https://www.daily.co/pricing)

Options for use when `start_cloud_recording` is `true`. See [`startRecording`](/reference/daily-js/instance-methods/start-recording) for available options.

⚠️ Specifying too many options may cause the token size to be very large. It is recommended to use token less than 2048 characters. For complex usecases, use the daily-js API.

`auto_start_transcription`

boolean

[Pay-as-you-go](https://www.daily.co/pricing)

Start transcription when an owner joins the room. This property can be used to always transcribe meetings once an owner joins.

Default: false

`close_tab_on_exit`

boolean

(For meetings that open in a separate browser tab.) When a user leaves a meeting using the button in the in-call menu bar, the browser tab closes. This can be a good way, especially on mobile, for users to be returned to a previous website flow after a call.

Default: false

`redirect_on_meeting_exit`

string

(For meetings that open in a separate browser tab.) When a user leaves a meeting using the button in the in-call menu bar, the browser loads this URL. A query string that includes a parameter of the form `recent-call=<domain>/<room>` is appended to the URL. On mobile, you can redirect to a deep link to bring a user back into your app.

`lang`

string

The default language of the [Daily prebuilt video call UI](https://docs.daily.co/docs/embed-the-daily-prebuilt-ui#daily-prebuilt-ui), for this room.

Setting the language at the token level will override any room or domain-level language settings you have.

Read more about [changing prebuilt UI language settings](https://help.daily.co/en/articles/4579930-changing-the-language-setting-of-the-prebuilt-ui).

`*` Norwegian `"no"` and Russian `"ru"` are only available in the new Daily Prebuilt.

Options: "da","de","en","es","fi","fr","it","jp","ka","nl","no","pt","pt-BR","pl","ru","sv","tr","user"

Default: en

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



## Example requests

### Create a token that grants access to a private room

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

### Create a token that configures screen sharing and recording

Here's how you might create a token that you use only for UI configuration with public rooms, not access control. This token enables screensharing, and recording, and could be used to give an "admin" user those features when joining a room that has them disabled by default. Notice that we don't set the `room_name`, so this token is valid for any room on your domain.

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/meeting-tokens/self-signing-tokens)

[Next](/reference/rest-api/meeting-tokens/validate-meeting-token)
