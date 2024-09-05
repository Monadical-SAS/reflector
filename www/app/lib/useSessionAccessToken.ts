"use client";

import { useState, useEffect } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { CustomSession } from "./types";

export default function useSessionAccessToken() {
  const { data: session } = useNextAuthSession();
  const customSession = session as CustomSession;
  const naAccessToken = customSession?.accessToken;
  const naAccessTokenExpires = customSession?.accessTokenExpires;
  const naError = customSession?.error;
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [accessTokenExpires, setAccessTokenExpires] = useState<number | null>(
    null,
  );
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (naAccessToken !== accessToken) {
      setAccessToken(naAccessToken);
    }
  }, [naAccessToken]);

  useEffect(() => {
    if (naAccessTokenExpires !== accessTokenExpires) {
      setAccessTokenExpires(naAccessTokenExpires);
    }
  }, [naAccessTokenExpires]);

  useEffect(() => {
    if (naError !== error) {
      setError(naError);
    }
  }, [naError]);

  return {
    accessToken,
    accessTokenExpires,
    error,
  };
}
