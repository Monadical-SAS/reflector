# Source: https://docs.daily.co/reference/rest-api/logs

# Logs

You can access call logs and metrics for every call to help you better understand your calls and troubleshoot issues as they arise.

Call logs characterize what happens on a call from the point of view of each participant. These logs include information about resource bundle downloads, signaling connections, [peer-to-peer & SFU call connections](/guides/intro-to-video-arch) and events, and participants' environments, actions, and error states.

Call metrics help to assess the performance and stability of the connection by providing transport layer, candidate-pair, and track level statistics.

Data starts being collected by the browser client once a second participant joins a call. The first data sample is logged after 15 seconds. Subsequent samples are logged every 15 seconds.

### **Accessing information**

Call logs and metrics are made available through the Daily [Dashboard](https://dashboard.daily.co) and the [`/logs` endpoint](/reference/rest-api/logs/list-logs).

Additionally, we've built a sample app — [Daily Call Explorer](https://colab.research.google.com/drive/1pMcB1I3YOhG7jcdH5ZrJk2VLb6cVzevm) — as an example of how this information can be used.

**More on logs and metrics**

  * [Introducing Dashboard Sessions, metrics, and logs](https://www.daily.co/blog/announcing-dashboard-sessions-metrics-and-logs/)
  * [Dive into call quality and beyond with the /logs endpoint](https://www.daily.co/blog/the-logs-endpoint-and-beyond/)


