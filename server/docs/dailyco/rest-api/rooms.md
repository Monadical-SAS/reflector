# Source: https://docs.daily.co/reference/rest-api/rooms

# The "room" object

A "room" represents a specific video call location and configuration. You can [list](/reference/rest-api/rooms/list-rooms), [create](/reference/rest-api/rooms/create-room), [configure](/reference/rest-api/rooms/set-room-config), and [delete](/reference/rest-api/rooms/delete-room) rooms with the Daily API.

Copy to clipboard

A room contains a `url` property. A participant joins a Daily video call via a room URL.

A room URL looks like this: `https://<your-domain>.daily.co/<room-name>/`.

A participant joins a Daily video call by opening the room URL directly in a browser tab (recommended for testing only), or by accessing the link from an embedded iframe ([Daily’s prebuilt UI](https://docs.daily.co/docs/embed-the-daily-prebuilt-ui)) or within a custom app [built on the Daily call object](/call-object).

**Heads up!**

Hard-coding Daily room URLs is fine for testing locally, but a security liability in production. You'll want to generate room URLs server side.

_Tutorial:[Deploying a Daily backend server instantly](https://www.daily.co/blog/deploy-a-daily-co-backend-node-js-server-instantly/) with Glitch and Node.js_.

Rooms can be created either [manually in the Daily dashboard](/guides/architecture-and-monitoring/experiment-in-the-dashboard#step-by-step-guide-create-a-daily-room-url-from-the-dashboard) or by a [POST to the /rooms API endpoint](/reference/rest-api/rooms/create-room).

You can specify [configuration properties](/reference/rest-api/rooms/config) when you create the room. All rooms come with a few default settings, unless you configure them otherwise.

By default, the `privacy` property is set to `"public"`. Anyone who knows the room's name can join the room, and anybody with access to the URL can enter. This is often what you want. It's easy to create rooms that have unique, unguessable, names. But, you can also change a room's privacy setting and [control who can join a room](/guides/controlling-who-joins-a-meeting).

**More resources on room privacy**

  * [Intro to room access control](https://www.daily.co/blog/intro-to-room-access-control/)
  * [Add advanced security to video chats with the Daily API](https://www.daily.co/blog/add-advanced-security-features-to-video-chats-with-the-daily-api/).



By default, rooms are permanent and always available. To limit that access, you can set two fields to control when participants can join a meeting in a room. `nbf` stands for "not before". If the `nbf` configuration field is set, participants can’t connect to the room before that time. `exp` is short for "expires." If the `exp` configuration flag is set, participants are not able to connect to the room after that time.

Note that `nbf` and `exp` only control whether users are allowed to _join_ a meeting in a room. Users who are in a meeting when a room expires are not kicked out of the meeting, unless you set the `eject_at_room_exp` property.

Rooms that have an exp in the past are not returned by the [list rooms endpoint](/reference/rest-api/rooms/list-rooms); they are zombies of a sort. An existing meeting can continue in the room, but from the perspective of most of the API, the room does not exist!

If you ever need to kick everyone out of a room unexpectedly, you can delete the room. (You can always recreate a room with the same name, later.)
