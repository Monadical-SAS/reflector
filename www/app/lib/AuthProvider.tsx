"use client";

import { createContext, useContext, useEffect } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { configureApiAuth } from "./apiClient";
import { CustomSession } from "./types";

type AuthContextType =
  | { status: "loading" }
  | { status: "unauthenticated"; error?: string }
  | {
      status: "authenticated";
      accessToken: string;
      accessTokenExpires: number;
    };

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useNextAuthSession();
  const customSession = session as CustomSession;

  if (session) {
    debugger;
  }

  const contextValue: AuthContextType =
    status === "loading"
      ? { status: "loading" as const }
      : customSession?.accessToken
        ? {
            status: "authenticated" as const,
            accessToken: customSession.accessToken,
            accessTokenExpires: customSession.accessTokenExpires,
          }
        : { status: "unauthenticated" as const };

  // not useEffect, we need it ASAP
  configureApiAuth(
    contextValue.status === "authenticated" ? contextValue.accessToken : null,
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
