# Source: https://docs.daily.co/reference/rest-api/meeting-tokens

# The "meeting token" object

"Meeting tokens" **control room access** and **session configuration** on a per-user basis.

A participant can join a non-public room with a valid meeting token. For private or public rooms, you can use meeting tokens to configure how a participant experiences the meeting (e.g. what call features are available).

You can [create](/reference/rest-api/meeting-tokens/create-meeting-token) and [validate](/reference/rest-api/meeting-tokens/validate-meeting-token) meeting tokens.

Copy to clipboard

Meeting token configuration properties set three things: room access, meeting time limits, and participant details, including their meeting permissions and available features.

## Room access

### `room_name`

**Always set`room_name`**

A meeting token without a `room_name` property allows access to _any_ room in your domain. Always set the `room_name` property when you are using meeting tokens to control room access.

See our guide to [controlling room access](/guides/controlling-who-joins-a-meeting) for more details.

Your tokens are unique to your domain and rooms. Tokens from another Daily domain can never grant access to your rooms.

### Meeting time limits

Two properties control how long a user is allowed to stay in a meeting.

If `eject_at_token_exp` is set to `true`, the user is kicked out of the meeting when the token expires. If the room is not public, then the user will not be able to rejoin the room.

The `eject_after_elapsed` property is the maximum number of seconds the user can stay in the meeting. The user will be kicked out `eject_after_elapsed` seconds after joining the meeting. If the meeting token has expired (and the room is not public) the user will not be able to rejoin the room. If the meeting token hasn't expired, of course, the user could reuse the meeting link and token to rejoin the room.

The two token properties `eject_at_token_exp` and `eject_after_elapsed` override the two room properties `eject_at_room_exp` and `eject_after_elapsed`. If either of the token properties are set, the two room properties are completely ignored for the current meeting session.

**Meeting time limits tutorial**

  * [Add advanced security to video chats with the Daily API](/guides/controlling-who-joins-a-meeting)



## Participant details, meeting permissions, and available features

You can use tokens to configure when a participant can join a meeting, when their access expires, and the call features that are enabled for each participant in a meeting. For example, you could set up a virtual classroom so that only one participant in the meeting (the teacher) can broadcast audio and video (to the students).

  * `nbf`
  * `exp`
  * `is_owner`
  * `user_name`
  * `user_id`
  * `enable_screenshare`
  * `start_video_off`
  * `start_audio_off`
  * `enable_recording`
  * `start_cloud_recording` [Pay-as-you-go](https://www.daily.co/pricing)
  * `close_tab_on_exit`
  * `redirect_on_meeting_exit`
  * `lang`



For a full descriptions of all properties, please see the [table below](/reference/rest-api/meeting-tokens/config).

## Using meeting tokens

To use a meeting token, pass it as a [property](/reference/daily-js/daily-call-client/properties) to the [factory method](/reference/daily-js/factory-methods) of your choice, or via the [`join()`](/reference/daily-js/instance-methods/join) method.

Setting a meeting token for a call participant via a factory or `join()` method property is the **only** way Daily recommends using meeting tokens, for security reasons.

For example, to give a specific participant special access when they join a meeting (e.g. admin privileges), you'd write something like:

Copy to clipboard

**Heads up!**

Don't forget to generate your meeting tokens server-side to keep production applications secure.

_Read about how to set up an[instant Daily server with Node.js and Glitch.](https://www.daily.co/blog/deploy-a-daily-co-backend-node-js-server-instantly/)_

Under the covers, meeting tokens are [JSON Web Tokens](https://jwt.io/). They are signed, but not encrypted, so you can decode the raw token yourself, if you're interested. Note that this means you should never put information that you want to keep secure into a meeting token.

You don't ever need to delete a meeting token. Meeting tokens are just cryptographically signed chunks of information that are validated by our API endpoints; they don't exist as server-side resources.

**Learn more about meeting tokens**

  * [Controlling who joins a meeting](/guides/controlling-who-joins-a-meeting)
  * [Intro to room access control](https://www.daily.co/blog/intro-to-room-access-control/)
  * [Add advanced security to video chats with the Daily API](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/)


