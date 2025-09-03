import { AuthOptions } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import type { JWT } from "next-auth/jwt";
import { JWTWithAccessToken, CustomSession } from "./types";
import {
  assertExists,
  assertExistsAndNonEmptyString,
  parseMaybeNonEmptyString,
} from "./utils";
import { REFRESH_ACCESS_TOKEN_ERROR } from "./auth";

const PRETIMEOUT = 600;

const tokenCache = new Map<
  string,
  { token: JWTWithAccessToken; timestamp: number }
>();
const TOKEN_CACHE_TTL = 60 * 60 * 24 * 30 * 1000; // 30 days in milliseconds

const refreshLocks = new Map<string, Promise<JWTWithAccessToken>>();

const CLIENT_ID = assertExistsAndNonEmptyString(
  process.env.AUTHENTIK_CLIENT_ID,
);
const CLIENT_SECRET = assertExistsAndNonEmptyString(
  process.env.AUTHENTIK_CLIENT_SECRET,
);

export const authOptions: AuthOptions = {
  providers: [
    AuthentikProvider({
      clientId: CLIENT_ID,
      clientSecret: CLIENT_SECRET,
      issuer: process.env.AUTHENTIK_ISSUER,
      authorization: {
        params: {
          scope: "openid email profile offline_access",
        },
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, account, user }) {
      const KEY = `token:${token.sub}`;

      if (account && user) {
        // called only on first login
        // XXX account.expires_in used in example is not defined for authentik backend, but expires_at is
        const expiresAtS = assertExists(account.expires_at) - PRETIMEOUT;
        const expiresAtMs = expiresAtS * 1000;
        if (!account.access_token) {
          tokenCache.delete(KEY);
        } else {
          const jwtToken: JWTWithAccessToken = {
            ...token,
            accessToken: account.access_token,
            accessTokenExpires: expiresAtMs,
            refreshToken: account.refresh_token,
          };
          // Store in memory cache
          tokenCache.set(KEY, {
            token: jwtToken,
            timestamp: Date.now(),
          });
          return jwtToken;
        }
      }

      const currentToken = tokenCache.get(KEY);
      if (currentToken && Date.now() < currentToken.token.accessTokenExpires) {
        return currentToken.token;
      }

      // access token has expired, try to update it
      return await lockedRefreshAccessToken(token);
    },
    async session({ session, token }) {
      const extendedToken = token as JWTWithAccessToken;
      return {
        ...session,
        accessToken: extendedToken.accessToken,
        accessTokenExpires: extendedToken.accessTokenExpires,
        error: extendedToken.error,
        user: {
          id: assertExists(extendedToken.sub),
          name: extendedToken.name,
          email: extendedToken.email,
        },
      } satisfies CustomSession;
    },
  },
};

async function lockedRefreshAccessToken(
  token: JWT,
): Promise<JWTWithAccessToken> {
  const lockKey = `${token.sub}-refresh`;

  const existingRefresh = refreshLocks.get(lockKey);
  if (existingRefresh) {
    return await existingRefresh;
  }

  const refreshPromise = (async () => {
    try {
      const cached = tokenCache.get(`token:${token.sub}`);
      if (cached) {
        if (Date.now() - cached.timestamp > TOKEN_CACHE_TTL) {
          tokenCache.delete(`token:${token.sub}`);
        } else if (Date.now() < cached.token.accessTokenExpires) {
          return cached.token;
        }
      }

      const currentToken = cached?.token || (token as JWTWithAccessToken);
      const newToken = await refreshAccessToken(currentToken);

      tokenCache.set(`token:${token.sub}`, {
        token: newToken,
        timestamp: Date.now(),
      });

      return newToken;
    } finally {
      setTimeout(() => refreshLocks.delete(lockKey), 100);
    }
  })();

  refreshLocks.set(lockKey, refreshPromise);
  return refreshPromise;
}

async function refreshAccessToken(token: JWT): Promise<JWTWithAccessToken> {
  try {
    const url = `${process.env.AUTHENTIK_REFRESH_TOKEN_URL}`;

    const options = {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: process.env.AUTHENTIK_CLIENT_ID as string,
        client_secret: process.env.AUTHENTIK_CLIENT_SECRET as string,
        grant_type: "refresh_token",
        refresh_token: token.refreshToken as string,
      }).toString(),
      method: "POST",
    };

    const response = await fetch(url, options);
    if (!response.ok) {
      console.error(
        new Date().toISOString(),
        "Failed to refresh access token. Response status:",
        response.status,
      );
      const responseBody = await response.text();
      console.error(new Date().toISOString(), "Response body:", responseBody);
      throw new Error(`Failed to refresh access token: ${response.statusText}`);
    }
    const refreshedTokens = await response.json();
    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires:
        Date.now() + (refreshedTokens.expires_in - PRETIMEOUT) * 1000,
      refreshToken: refreshedTokens.refresh_token,
    };
  } catch (error) {
    console.error("Error refreshing access token", error);
    return {
      ...token,
      error: REFRESH_ACCESS_TOKEN_ERROR,
    } as JWTWithAccessToken;
  }
}
