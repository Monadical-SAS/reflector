/**
 * This is a custom hook that automatically refreshes the session when the access token is about to expire.
 * When communicating with the reflector API, we need to ensure that the access token is always valid.
 *
 * We could have implemented that as an interceptor on the API client, but not everything is using the
 * API client, or have access to NextJS directly (serviceWorker).
 */
"use client";

import { useSession } from "next-auth/react";
import { useEffect } from "react";
import { CustomSession } from "./types";

export function SessionAutoRefresh({
  children,
  refreshInterval = 20 /* seconds */,
}) {
  const { data: session, update } = useSession();
  const customSession = session as CustomSession;
  const accessTokenExpires = customSession?.accessTokenExpires;

  useEffect(() => {
    const interval = setInterval(() => {
      if (accessTokenExpires) {
        const timeLeft = accessTokenExpires - Date.now();
        if (timeLeft < refreshInterval * 1000) {
          update();
        }
      }
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [accessTokenExpires, refreshInterval, update]);

  return children;
}
