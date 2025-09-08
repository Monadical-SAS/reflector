/**
 * This is a custom provider that automatically refreshes the session when the access token is about to expire.
 * When communicating with the reflector API, we need to ensure that the access token is always valid.
 *
 * We could have implemented that as an interceptor on the API client, but not everything is using the
 * API client, or have access to NextJS directly (serviceWorker).
 */
"use client";

import { useEffect } from "react";
import { useAuth } from "./AuthProvider";
import { shouldRefreshToken } from "./auth";

export function SessionAutoRefresh({ children }) {
  const auth = useAuth();

  const accessTokenExpires =
    auth.status === "authenticated" ? auth.accessTokenExpires : null;

  useEffect(() => {
    // technical value for how often the setInterval will be polling news - not too fast (no spam in case of errors)
    // and not too slow (debuggable)
    const INTERVAL_REFRESH_MS = 5000;
    const interval = setInterval(() => {
      if (accessTokenExpires === null) return;
      if (shouldRefreshToken(accessTokenExpires)) {
        auth
          .update()
          .then(() => {})
          .catch((e) => {
            // note: 401 won't be considered error here
            console.error("error refreshing auth token", e);
          });
      }
    }, INTERVAL_REFRESH_MS);

    return () => clearInterval(interval);
  }, [accessTokenExpires, auth.update]);

  return children;
}
