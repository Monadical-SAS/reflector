let authToken = null;

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SET_AUTH_TOKEN") {
    authToken = event.data.token;
  }
});

self.addEventListener("fetch", function (event) {
  // Check if the request is for a media file
  if (/\/v1\/transcripts\/.*\/audio\/mp3$/.test(event.request.url)) {
    // Modify the request to add the Authorization header
    const modifiedHeaders = new Headers(event.request.headers);
    if (authToken) {
      modifiedHeaders.append("Authorization", `Bearer ${authToken}`);
    }

    const modifiedRequest = new Request(event.request, {
      headers: modifiedHeaders,
    });

    // Respond with the modified request
    event.respondWith(fetch(modifiedRequest));
  }
});
