"use client";

import { createContext, useContext } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { signOut, signIn } from "next-auth/react";
import { configureApiAuth } from "./apiClient";
import { assertCustomSession, CustomSession } from "./types";
import { Session } from "next-auth";
import { SessionAutoRefresh } from "./SessionAutoRefresh";
import { REFRESH_ACCESS_TOKEN_ERROR } from "./auth";

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
  const customSession = session ? assertCustomSession(session) : null;

  const contextValue: AuthContextType = {
    ...(() => {
      switch (status) {
        case "loading": {
          const sessionIsHere = !!customSession;
          switch (sessionIsHere) {
            case false: {
              return { status };
            }
            case true: {
              return { status: "refreshing" as const };
            }
            default: {
              const _: never = sessionIsHere;
              throw new Error("unreachable");
            }
          }
        }
        case "authenticated": {
          if (customSession?.error === REFRESH_ACCESS_TOKEN_ERROR) {
            // token had chance to expire but next auth still returns "authenticated" so show user unauthenticated state
            return {
              status: "unauthenticated" as const,
            };
          } else if (customSession?.accessToken) {
            return {
              status,
              accessToken: customSession.accessToken,
              accessTokenExpires: customSession.accessTokenExpires,
              user: customSession.user,
            };
          } else {
            console.warn(
              "illegal state: authenticated but have no session/or access token. ignoring",
            );
            return { status: "unauthenticated" as const };
          }
        }
        case "unauthenticated": {
          return { status: "unauthenticated" as const };
        }
        default: {
          const _: never = status;
          throw new Error("unreachable");
        }
      }
    })(),
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
