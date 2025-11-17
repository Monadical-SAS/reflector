# Source: https://docs.daily.co/reference/rest-api/rooms/recordings

#

Recordings

[Pay-as-you-go](https://www.daily.co/pricing)

You can [start](/reference/rest-api/rooms/recordings/start), [update](/reference/rest-api/rooms/recordings/update), or [stop](/reference/rest-api/rooms/recordings/stop) a recording with the Daily API.

This set of endpoints can start `"cloud"` or `"raw-tracks"` recordings. It will default to `"cloud"` recordings. You can use the [recordings](/reference/rest-api/recordings) endpoints to get more information about the status of a given recording.

The endpoints are mostly equivalent to the [`startRecording()`](/reference/daily-js/instance-methods/start-recording), [`updateRecording()`](/reference/daily-js/instance-methods/update-recording), and [`stopRecording()`](/reference/daily-js/instance-methods/stop-recording) calls found in our [`daily-js`](/reference/daily-js) library.

Head to our **[recordings guide](/guides/recording-calls-with-the-daily-api)** for detailed information on using recordings.
