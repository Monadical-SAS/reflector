"use client";

import { useEffect } from "react";
import { configureApiAuth } from "./apiClient";
import useSessionAccessToken from "./useSessionAccessToken";

// Note: Base URL is now configured directly in apiClient.tsx

export function ApiAuthProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useSessionAccessToken();

  useEffect(() => {
    // Configure authentication
    configureApiAuth(accessToken);
  }, [accessToken]);

  return <>{children}</>;
}
