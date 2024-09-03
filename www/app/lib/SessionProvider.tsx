"use client";
import { SessionProvider as SessionProviderNextAuth } from "next-auth/react";
import { SessionAutoRefresh } from "./SessionAutoRefresh";

export default function SessionProvider({ children }) {
  return (
    <SessionProviderNextAuth refetchInterval={60} refetchOnWindowFocus={true}>
      <SessionAutoRefresh>{children}</SessionAutoRefresh>
    </SessionProviderNextAuth>
  );
}
