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

export function SessionAutoRefresh({
  children,
  refreshInterval = 20 /* seconds */,
}) {
  const auth = useAuth();
  const accessTokenExpires =
    auth.status === "authenticated" ? auth.accessTokenExpires : null;

  const refreshIntervalMs = refreshInterval * 1000;

  useEffect(() => {
    const interval = setInterval(() => {
      if (accessTokenExpires !== null) {
        const timeLeft = accessTokenExpires - Date.now();
        if (timeLeft < refreshIntervalMs) {
          auth.update();
        }
      }
    }, refreshIntervalMs);

    return () => clearInterval(interval);
  }, [accessTokenExpires, refreshInterval, auth.update]);

  return children;
}
