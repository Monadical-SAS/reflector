"use client";

import { createContext, useContext, useRef } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { signOut, signIn } from "next-auth/react";
import { configureApiAuth } from "./apiClient";
import { assertCustomSession, CustomSession } from "./types";
import { Session } from "next-auth";
import { SessionAutoRefresh } from "./SessionAutoRefresh";
import { REFRESH_ACCESS_TOKEN_ERROR } from "./auth";
import { assertExists } from "./utils";
import { featureEnabled } from "./features";

type AuthContextType = (
  | { status: "loading" }
  | { status: "refreshing"; user: CustomSession["user"] }
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
  // TODO probably rename isLoading to isReloading and make THIS field "isLoading"
  lastUserId: CustomSession["user"]["id"] | null;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const isAuthEnabled = featureEnabled("requireLogin");

const noopAuthContext: AuthContextType = {
  status: "unauthenticated",
  update: async () => {
    return null;
  },
  signIn: async () => {
    throw new Error("signIn not supposed to be called");
  },
  signOut: async () => {
    throw new Error("signOut not supposed to be called");
  },
  lastUserId: null,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status, update } = useNextAuthSession();
  // referential comparison done in component, must be primitive /or cached
  const lastUserId = useRef<CustomSession["user"]["id"] | null>(null);

  const contextValue: AuthContextType = isAuthEnabled
    ? {
        ...(() => {
          switch (status) {
            case "loading": {
              const sessionIsHere = !!session;
              // actually exists sometimes; nextAuth types are something else
              switch (sessionIsHere as boolean) {
                case false: {
                  return { status };
                }
                case true: {
                  return {
                    status: "refreshing" as const,
                    user: assertCustomSession(
                      assertExists(session as unknown as Session),
                    ).user,
                  };
                }
                default: {
                  throw new Error("unreachable");
                }
              }
            }
            case "authenticated": {
              const customSession = assertCustomSession(session);
              if (customSession?.error === REFRESH_ACCESS_TOKEN_ERROR) {
                // token had expired but next auth still returns "authenticated" so show user unauthenticated state
                return {
                  status: "unauthenticated" as const,
                };
              } else if (customSession?.accessToken) {
                // updates anyways with updated properties below
                // warning! execution order conscience, must be ran before reading lastUserId.current below
                lastUserId.current = customSession.user.id;
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
        // for optimistic cases when we assume "loading" doesn't immediately invalidate the user
        lastUserId: lastUserId.current,
      }
    : noopAuthContext;

  // not useEffect, we need it ASAP
  // apparently, still no guarantee this code runs before mutations are fired
  configureApiAuth(
    contextValue.status === "authenticated"
      ? contextValue.accessToken
      : contextValue.status === "loading"
        ? undefined
        : null,
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
