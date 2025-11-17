# Source: https://docs.daily.co/reference/rest-api/meeting-tokens/self-signing-tokens

# Self-signing tokens

If you're unfamiliar with JWTs and how to create them, please use the existing `/meeting-tokens` endpoints.

## Generating self-signed tokens

Using your [API key](https://dashboard.daily.co/developers), you can self-sign tokens that will be accepted by the backend, as long as the API key is still active at the time it is checked. This saves making a round-trip to the Daily API to generate tokens, which is great if you need to update the tokens often or create them in bulk.

You can create a JWT using your domain's API key as the secret and making the payload include a room name ("`r`"), the current time ("`iat`"), and the domain_id ("`d`") like:

`{ "r": "test", "iat": 1610596413, "d": "30f866c3-9123-452a-8723-ff58322d09c5"}`

Note: The `domain_id` is available from the domain configuration [endpoint](/reference/rest-api/your-domain/get-domain-config).

To learn more about, and test, your tokens please refer to <https://jwt.io/>.

**Configuration[properties](/reference/rest-api/meeting-tokens/config) in tokens use the following abbreviations:**

Property| abbreviated
---|---
`nbf`| `nbf`
`exp`| `exp`
`domain_id`| `d`
`room_name`| `r`
`user_id`| `ud`
`user_name`| `u`
`is_owner`| `o`
`knocking`| `k`
`close_tab_on_exit`| `ctoe`
`redirect_on_meeting_exit`| `rome`
`intercom_join_alert`| `ij`
`start_cloud_recording`| `sr`
`start_cloud_recording_opts`| `sro`
`auto_start_transcription`| `ast`
`enable_recording`| `er`
`enable_screenshare`| `ss`
`start_video_off`| `vo`
`start_audio_off`| `ao`
`meeting_join_hook`| `mjh`
`eject_at_token_exp`| `ejt`
`eject_after_elapsed`| `eje`
`lang`| `uil`
`enable_recording_ui`| `erui`
`permissions`| `p`

**The[`permissions`](/reference/rest-api/meeting-tokens/config#permissions) property in tokens uses the following abbreviations:**

Copy to clipboard

* * *

[Previous](/reference/rest-api/meeting-tokens/config)

[Next](/reference/rest-api/meeting-tokens/create-meeting-token)
