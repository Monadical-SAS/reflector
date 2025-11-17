# Source: https://docs.daily.co/reference/rest-api/domainDialinConfig/update-domain-dialin-config

#

PUT

/domain-dialin-config/:updateId

**A`PUT` request to `/domain-dialin-config/:updateId` update an new pinless_dialin and pin_dialin config.**

Any of the property associated with config can be updated, e.g. hold music, ivr_greeting, etc. However, to move a phone number between pinless_dialin and pin_dialin categories, you will first need to delete the existing config and then recreating the config in the new category.

## Example request

### update config

## Body params

`phone_number`

string

The phone number to configure for pinless_dialin or pin_dialin. If the same number is used by any other config then the API will fail. Required for pinless_dialin, optional for pin_dialin.

`name_prefix`

string

friendly name for the configuration.

`hmac`

string

The [HMAC signature](/guides/products/dial-in-dial-out/dialin-pinless#hmac) used to verify the webhook called to "room_creation_api". (only for pinless_dialin type)

`room_creation_api`

string

The API to request when a call is received on configured phoneNumber or sip_uri. (only for pinless_dialin type). flow is described [here](/guides/products/dial-in-dial-out/dialin-pinless.mdx#quick-overview)

`hold_music_url`

string

The URL to the hold music to play when the call is received, (only for pinless_dialin type). The hold music must be a publicly accessible URL in MP3 format. The hold music must be less than 10MB in size and less than 60 seconds in duration. In pinless_dialin, the hold music will be played twice.

`timeout_config`

object

The timeout configuration for the dialin config.

`message`

string

If room_creation_api does not respond within the timeout period, this message will be played to the caller.

`ivr_greeting`

object

configuration when the call is received on phone number (only for pin_dialin).

`message`

string

The message to play when call first connects.

## Response Body Parameters

`id`

string

A unique, opaque ID for this object. You can use this ID in API calls, and in paginated list operations.

`type`

string

describes the type of configuration. It can be pinless_dialin or pin_dialin.

Options: "pinless_dialin","pin_dialin"

`config`

object

the configuration object passed to the POST API that creates the dialin config.

`phone_number`

string

The phone number to configure for pinless_dialin or pin_dialin. If the same number is used by any other config then the API will fail. Required for pinless_dialin, optional for pin_dialin.

`name_prefix`

string

friendly name for the configuration.

`hmac`

string

The [HMAC signature](/guides/products/dial-in-dial-out/dialin-pinless#hmac) used to verify the webhook called to "room_creation_api". (only for pinless_dialin type)

`room_creation_api`

string

The API to request when a call is received on configured phoneNumber or sip_uri. (only for pinless_dialin type). flow is described [here](/guides/products/dial-in-dial-out/dialin-pinless.mdx#quick-overview)

`hold_music_url`

string

The URL to the hold music to play when the call is received, (only for pinless_dialin type). The hold music must be a publicly accessible URL in MP3 format. The hold music must be less than 10MB in size and less than 60 seconds in duration. In pinless_dialin, the hold music will be played twice.

`timeout_config`

object

The timeout configuration for the dialin config.

`message`

string

If room_creation_api does not respond within the timeout period, this message will be played to the caller.

`ivr_greeting`

object

configuration when the call is received on phone number (only for pin_dialin).

`message`

string

The message to play when call first connects.

## Example requests

## Body params

`phone_number`

string

The phone number to configure for pinless_dialin or pin_dialin. If the same number is used by any other config then the API will fail. Required for pinless_dialin, optional for pin_dialin.

`name_prefix`

string

friendly name for the configuration.

`hmac`

string

The [HMAC signature](/guides/products/dial-in-dial-out/dialin-pinless#hmac) used to verify the webhook called to "room_creation_api". (only for pinless_dialin type)

`room_creation_api`

string

The API to request when a call is received on configured phoneNumber or sip_uri. (only for pinless_dialin type). flow is described [here](/guides/products/dial-in-dial-out/dialin-pinless.mdx#quick-overview)

`hold_music_url`

string

The URL to the hold music to play when the call is received, (only for pinless_dialin type). The hold music must be a publicly accessible URL in MP3 format. The hold music must be less than 10MB in size and less than 60 seconds in duration. In pinless_dialin, the hold music will be played twice.

`timeout_config`

object

The timeout configuration for the dialin config.

`message`

string

If room_creation_api does not respond within the timeout period, this message will be played to the caller.

`ivr_greeting`

object

configuration when the call is received on phone number (only for pin_dialin).

`message`

string

The message to play when call first connects.

## Response Body Parameters

`id`

string

A unique, opaque ID for this object. You can use this ID in API calls, and in paginated list operations.

`type`

string

describes the type of configuration. It can be pinless_dialin or pin_dialin.

Options: "pinless_dialin","pin_dialin"

`config`

object

the configuration object passed to the POST API that creates the dialin config.

`phone_number`

string

The phone number to configure for pinless_dialin or pin_dialin. If the same number is used by any other config then the API will fail. Required for pinless_dialin, optional for pin_dialin.

`name_prefix`

string

friendly name for the configuration.

`hmac`

string

The [HMAC signature](/guides/products/dial-in-dial-out/dialin-pinless#hmac) used to verify the webhook called to "room_creation_api". (only for pinless_dialin type)

`room_creation_api`

string

The API to request when a call is received on configured phoneNumber or sip_uri. (only for pinless_dialin type). flow is described [here](/guides/products/dial-in-dial-out/dialin-pinless.mdx#quick-overview)

`hold_music_url`

string

The URL to the hold music to play when the call is received, (only for pinless_dialin type). The hold music must be a publicly accessible URL in MP3 format. The hold music must be less than 10MB in size and less than 60 seconds in duration. In pinless_dialin, the hold music will be played twice.

`timeout_config`

object

The timeout configuration for the dialin config.

`message`

string

If room_creation_api does not respond within the timeout period, this message will be played to the caller.

`ivr_greeting`

object

configuration when the call is received on phone number (only for pin_dialin).

`message`

string

The message to play when call first connects.

## Example requests

**Request**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

[Previous](/reference/rest-api/domainDialinConfig/create-dialin-config)

[Next](/reference/rest-api/domainDialinConfig/get-domain-dialin-config)
