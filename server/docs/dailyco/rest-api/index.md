# Source: https://docs.daily.co/reference/rest-api

# REST API

Your domain's API key is available in the **Developers** section of the Daily [dashboard](https://dashboard.daily.co/).

Domain owners can view and regenerate your team's API key.

Members do not have access to your team's API key.

Need a staging key? [Learn more here](https://help.daily.co/en/articles/4208047-api-key-for-staging-or-testing).

If you're a member and you require access, request the key from a team member or request administrator privileges from one of your team's admins.

HTTPS is required for all Daily REST API requests.

## Authentication

**The Daily API uses API keys to authenticate requests.**

Almost all of the Daily API endpoints require that you include your API key in the `Authorization` header of your HTTPS request. For example:

Copy to clipboard

Each API key is tied to a specific Daily domain.

You should keep your API key secret. **Never use the API key in client-side web browser code** , for example.

If an API call requires authentication, but no `Authorization: Bearer` header is present, we return an HTTP `400` error, with a body that includes an `error` parameter set to the string `"authorization-header-error"`.

If an API call requires authentication but the API key provided in the authorization header isn't valid, we return an HTTP `401` error, with a body that includes an `error` parameter set to the string `"authentication-error"`.

## Rate limits

Daily uses rate limiting to ensure the stability of the API across all of Daily's users. If you make lots of requests in succession, you may see `429` status codes returned by the API. Daily has two levels of rate limiting, each of which affect different endpoints.

  * For most of our API endpoints, you can expect a limit of `20` requests per second, or `100` requests over a `5` second window.
  * For the [DELETE /rooms/:name](/reference/rest-api/rooms/delete-room) and [GET /recordings](/reference/rest-api/recordings/list-recordings) endpoints, you can expect about `2` requests per second, or `50` requests over a `30` second window.
  * For starting a Recording, Livestreaming, PSTN, and SIP call, you can expect about `1` requests per second, or `5` requests over a `5` second window. For example, you can start a recording and initiate a PSTN dial-out immediately when the first participant joins a call, so it is possible to do a burst of requests as long as you are within the 5 requests in that 5 second window.



You should attempt to retry `429` status codes in order to handle limiting gracefully. A good technique to apply here is to retry your requests with an [exponential backoff schedule](https://en.wikipedia.org/wiki/Exponential_backoff) to help reduce your request volume over each window. Many HTTP clients offer this as a configuration option out of the box.

In order to ensure stability and prevent abuse, we may alter the stated limits. [Contact support](https://www.daily.co/contact/support) if you need to increase your API limits.

## Errors

The Daily API endpoints all return errors, wherever possible, as HTTP `4xx` or `5xx` error responses.

Error response bodies generally includes two parameters: `error`, and `info`. The `error` parameter is a string indicating an error type, and the `info` parameter fills in a bit more human readable information, wherever available.

The `error` types are stable; we don't expect to change them (though we'll likely add new error types over time.) But please treat the `info` strings only as additional information you use while developing and debugging. Content of the `info` parameter is _not_ fixed and may change as we improve error feedback.

Copy to clipboard

### HTTP status codes

HTTP status code| Response| Interpretation
---|---|---
200| OK| Everything worked as expected.
400| Bad Request| The operation could not be performed as requested.
401| Unauthorized| The provided API key was not valid.
403| Forbidden| The API key was valid but the requested resource was forbidden.
404| Not Found| The requested REST resource did not exist.
429| Too Many Requests| Too many requests were sent in too short a period of time. Please throttle your request rate.
5xx| Server Errors| Something unexpected happened on the server side. Please ping us to report this, if possible.

### Error types

Error string| Description
---|---
authentication-error| The API key is not valid.
authorization-header-error| The Authorization header is missing or badly formatted.
forbidden-error| The API key is valid but the requested resource is forbidden.
json-parsing-error| The JSON request body could not be parsed.
invalid-request-error| The request could not be performed. More information is usually available in the info field of the response body. Typical causes are missing required parameters, bad parameter values, etc.
rate-limit-error| Too many requests were sent in too short a period of time. Please throttle your request rate.
server-error| Something unexpected went wrong.

## Pagination

### Fetching 100 results at a time

The [list rooms](/reference/rest-api/rooms/list-rooms) and [list recordings](/reference/rest-api/recordings/list-recordings) API endpoints return a maximum of 100 data objects at one time, and accept pagination arguments in their query strings.

All pagination arguments are optional. Without any pagination arguments, the list methods return up to 100 data objects, sorted in reverse chronological order by creation time. (In other words, by default, you just get back a list of your most recently created room or recording objects!)

It's helpful to think of pagination arguments — as the name suggests — in terms of defining "pages" of results.

  * The `limit` argument sets the size of the page (how many objects each page contains), and defaults to a value of 100.
  * The `starting_after` argument sets the starting point of the page and is used to fetch "subsequent" pages of results – as if you were paging through a book from front to back.
  * The `ending_before` argument is the opposite, and is used to fetch previous pages of results -- as if you were paging through a book from back to front.
  * A special `ending_before` argument, `OLDEST`, is available to facilitate fetching pages of results "backwards," from oldest objects to newest.



Note that the granularity for `created_at` timestamps is one second. The returned list order is stable, because `id` is the secondary sort field. But if you create multiple rooms within a 1-second window, the list order may not be _precisely_ reverse-chronological.

Pagination argument| Description
---|---
limit| A limit on the number of objects to be returned. Maximum value is 100. Default value (if not supplied) is 100.
starting_after| An object ID to be used as a pagination cursor. The first object returned will be the object immediately after the object this id. This argument is commonly used to fetch the "next" page of results.
ending_before| The opposite of starting_after. The last page of returned results will be the object immediately preceding the object with this id. The special value OLDEST fetches the "last" page of results (the page containing the objects created longest ago).

### Examples

Copy to clipboard

Copy to clipboard

### Pseudocode for fetching until there are no more results available

Here's what code looks like that fetches and does something will all of your room objects. We've left error checking as an exercise for the reader.

Copy to clipboard
