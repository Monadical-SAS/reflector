# Source: https://docs.daily.co/reference/rest-api/meetings

# Meetings

## The "meeting" object

Copy to clipboard

A meeting session is a set of one or more people in a room together during a specific time window.

Meeting session objects contain information about who joined calls in your rooms, when, and for how long.

Each meeting session object has six fields:

  * A unique, opaque meeting session `id`
  * The name of the `room`
  * A `start_time` (when the first user joined the session)
  * A `duration`
  * An `ongoing` boolean (true, if any participants are currently in the room)
  * A `max_participants` value (number), for the maximum number of participants that were present in the meeting at one time
  * A list of meeting session `participants`



The objects in the `participants` list five fields: `join_time`, `duration`, `participant_id`, `user_id`, and `user_name`. `join_time`, `duration`, and `participant_id` will always contain valid data. `user_id` and `user_name` fields will be `null` if that information is not available for the participant.

The `start_time` and `join_time` fields are unix timestamps (seconds since the epoch), and have approximately 15-second granularity. (We generally do not write a "meeting join" record until a user has stayed in a room for at least 10 seconds. ) The `duration` fields are elapsed times in seconds.

Because rooms are often reused, the definition of a meeting session needs to account for what happens when people join and leave rooms in arbitrary sequences. Here are the rules that determine the start and end bounds of a meeting session: A new meeting session begins when:

  * A single participant joins the room and has been alone for 30 seconds.
  * A second participant joins the room prior to the 30 seconds.
  * A participant remains in a room alone for 10 minutes after all others have left



A meeting session ends when:

  * All users leave the room. (The participant count is zero)
  * A participant remains in a room alone for 10 minutes after all others have left. (The participant count decrements to 1 for 10 minutes)



The intent of 10 minute reset is to try to match users expectations about what a "meeting" is. Some of our users leave rooms open for long periods of time, and stay in that room, and then are periodically joined by other people for "meetings." Thus, a user's unbroken time in a room might span multiple meeting sessions.

Copy to clipboard
