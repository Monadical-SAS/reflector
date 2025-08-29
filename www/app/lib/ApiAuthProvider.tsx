"use client";

import { useEffect } from "react";
import { configureApiAuth } from "./apiClient";
import useSessionAccessToken from "./useSessionAccessToken";

export function ApiAuthProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useSessionAccessToken();

  useEffect(() => {
    configureApiAuth(accessToken);
  }, [accessToken]);

  return <>{children}</>;
}
