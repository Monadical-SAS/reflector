"use client";

import { createContext, useContext } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { signOut, signIn } from "next-auth/react";
import { configureApiAuth } from "./apiClient";
import { assertExtendedTokenAndUserId, CustomSession } from "./types";
import { Session } from "next-auth";
import { SessionAutoRefresh } from "./SessionAutoRefresh";

type AuthContextType = (
  | { status: "loading" }
  | { status: "refreshing" }
  | { status: "unauthenticated"; error?: string }
  | {
      status: "authenticated";
      accessToken: string;
      accessTokenExpires: number;
      user: CustomSession["user"];
    }
) & {
  update: () => Promise<Session | null>;
  signIn: typeof signIn;
  signOut: typeof signOut;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status, update } = useNextAuthSession();
  const customSession = session ? assertExtendedTokenAndUserId(session) : null;

  const contextValue: AuthContextType = {
    ...(status === "loading" && !customSession
      ? { status }
      : status === "loading" && customSession
        ? { status: "refreshing" as const }
        : status === "authenticated" && customSession?.accessToken
          ? {
              status,
              accessToken: customSession.accessToken,
              accessTokenExpires: customSession.accessTokenExpires,
              user: customSession.user,
            }
          : status === "authenticated" && !customSession?.accessToken
            ? (() => {
                console.warn(
                  "illegal state: authenticated but have no session/or access token. ignoring",
                );
                return { status: "unauthenticated" as const };
              })()
            : { status: "unauthenticated" as const }),
    update,
    signIn,
    signOut,
  };

  // not useEffect, we need it ASAP
  configureApiAuth(
    contextValue.status === "authenticated" ? contextValue.accessToken : null,
  );

  return (
    <AuthContext.Provider value={contextValue}>
      <SessionAutoRefresh>{children}</SessionAutoRefresh>
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
