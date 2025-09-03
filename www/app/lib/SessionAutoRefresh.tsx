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
import { REFRESH_ACCESS_TOKEN_BEFORE } from "./auth";

const REFRESH_BEFORE = REFRESH_ACCESS_TOKEN_BEFORE;

export function SessionAutoRefresh({ children }) {
  const auth = useAuth();
  const accessTokenExpires =
    auth.status === "authenticated" ? auth.accessTokenExpires : null;

  useEffect(() => {
    const interval = setInterval(() => {
      if (accessTokenExpires !== null) {
        const timeLeft = accessTokenExpires - Date.now();
        if (timeLeft < REFRESH_BEFORE) {
          auth
            .update()
            .then(() => {})
            .catch((e) => {
              // note: 401 won't be considered error here
              console.error("error refreshing auth token", e);
            });
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [accessTokenExpires, auth.update]);

  return children;
}
