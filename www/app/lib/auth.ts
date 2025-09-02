import { AuthOptions } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import { JWT } from "next-auth/jwt";
import {
  JWTWithAccessToken,
  CustomSession,
  assertExtendedToken,
} from "./types";
import {
  assertExistsAndNonEmptyString,
  parseMaybeNonEmptyString,
} from "./utils";

const PRETIMEOUT = 60; // seconds before token expires to refresh it

// Simple in-memory cache for tokens (in production, consider using a proper cache solution)
const tokenCache = new Map<
  string,
  { token: JWTWithAccessToken; timestamp: number }
>();
const TOKEN_CACHE_TTL = 60 * 60 * 24 * 30 * 1000; // 30 days in milliseconds

// Simple lock mechanism to prevent concurrent token refreshes
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
      const extendedToken = assertExtendedToken(token);
      const KEY = `token:${token.sub}`;
      if (account && user) {
        // called only on first login
        // XXX account.expires_in used in example is not defined for authentik backend, but expires_at is
        const expiresAt = (account.expires_at as number) - PRETIMEOUT;
        if (!account.access_token) {
          tokenCache.delete(KEY);
        } else {
          const jwtToken: JWTWithAccessToken = {
            ...extendedToken,
            accessToken: account.access_token,
            accessTokenExpires: expiresAt * 1000,
            refreshToken: account.refresh_token || "",
          };
          // Store in memory cache
          tokenCache.set(`token:${jwtToken.sub}`, {
            token: jwtToken,
            timestamp: Date.now(),
          });
          return jwtToken;
        }
      }

      if (Date.now() < extendedToken.accessTokenExpires) {
        return token;
      }

      // access token has expired, try to update it
      return await lockedRefreshAccessToken(token);
    },
    async session({ session, token }) {
      const extendedToken = token as JWTWithAccessToken;
      const customSession = session as CustomSession;
      customSession.accessToken = extendedToken.accessToken;
      customSession.accessTokenExpires = extendedToken.accessTokenExpires;
      customSession.error = extendedToken.error;
      customSession.user = {
        id: extendedToken.sub,
        name: extendedToken.name,
        email: extendedToken.email,
      };
      return customSession;
    },
  },
};

async function lockedRefreshAccessToken(
  token: JWT,
): Promise<JWTWithAccessToken> {
  const lockKey = `${token.sub}-refresh`;

  // Check if there's already a refresh in progress
  const existingRefresh = refreshLocks.get(lockKey);
  if (existingRefresh) {
    return existingRefresh;
  }

  // Create a new refresh promise
  const refreshPromise = (async () => {
    try {
      // Check cache for recent token
      const cached = tokenCache.get(`token:${token.sub}`);
      if (cached) {
        // Clean up old cache entries
        if (Date.now() - cached.timestamp > TOKEN_CACHE_TTL) {
          tokenCache.delete(`token:${token.sub}`);
        } else if (Date.now() < cached.token.accessTokenExpires) {
          // Token is still valid
          return cached.token;
        }
      }

      // Refresh the token
      const currentToken = cached?.token || (token as JWTWithAccessToken);
      const newToken = await refreshAccessToken(currentToken);

      // Update cache
      tokenCache.set(`token:${token.sub}`, {
        token: newToken,
        timestamp: Date.now(),
      });

      return newToken;
    } finally {
      // Clean up the lock after a short delay
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
      error: "RefreshAccessTokenError",
    } as JWTWithAccessToken;
  }
}
