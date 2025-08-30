"use client";

import { useSession as useNextAuthSession } from "next-auth/react";
import { CustomSession } from "./types";

export default function useSessionAccessToken() {
  const { data: session } = useNextAuthSession();
  const customSession = session as CustomSession;

  return {
    accessToken: customSession?.accessToken ?? null,
    accessTokenExpires: customSession?.accessTokenExpires ?? null,
    error: customSession?.error,
  };
}
