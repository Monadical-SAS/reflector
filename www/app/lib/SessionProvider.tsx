"use client";
import { SessionProvider as SessionProviderNextAuth } from "next-auth/react";
import { SessionAutoRefresh } from "./SessionAutoRefresh";

export default function SessionProvider({ children }) {
  return (
    <SessionProviderNextAuth>
      <SessionAutoRefresh>{children}</SessionAutoRefresh>
    </SessionProviderNextAuth>
  );
}
