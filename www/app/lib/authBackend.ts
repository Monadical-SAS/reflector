import { AuthOptions } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import type { JWT } from "next-auth/jwt";
import { JWTWithAccessToken, CustomSession } from "./types";
import {
  assertExists,
  assertExistsAndNonEmptyString,
  assertNotExists,
} from "./utils";
import {
  REFRESH_ACCESS_TOKEN_BEFORE,
  REFRESH_ACCESS_TOKEN_ERROR,
  shouldRefreshToken,
} from "./auth";
import {
  getTokenCache,
  setTokenCache,
  deleteTokenCache,
} from "./redisTokenCache";
import { tokenCacheRedis, redlock } from "./redisClient";
import { isBuildPhase } from "./next";

const TOKEN_CACHE_TTL = REFRESH_ACCESS_TOKEN_BEFORE;
const CLIENT_ID = !isBuildPhase
  ? assertExistsAndNonEmptyString(
      process.env.AUTHENTIK_CLIENT_ID,
      "AUTHENTIK_CLIENT_ID required",
    )
  : "noop";
const CLIENT_SECRET = !isBuildPhase
  ? assertExistsAndNonEmptyString(
      process.env.AUTHENTIK_CLIENT_SECRET,
      "AUTHENTIK_CLIENT_SECRET required",
    )
  : "noop";

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
      if (account && !account.access_token) {
        await deleteTokenCache(tokenCacheRedis, `token:${token.sub}`);
      }

      if (account && user) {
        // called only on first login
        // XXX account.expires_in used in example is not defined for authentik backend, but expires_at is
        if (account.access_token) {
          const expiresAtS = assertExists(account.expires_at);
          const expiresAtMs = expiresAtS * 1000;
          const jwtToken: JWTWithAccessToken = {
            ...token,
            accessToken: account.access_token,
            accessTokenExpires: expiresAtMs,
            refreshToken: account.refresh_token,
          };
          if (jwtToken.error) {
            await deleteTokenCache(tokenCacheRedis, `token:${token.sub}`);
          } else {
            assertNotExists(
              jwtToken.error,
              `panic! trying to cache token with error in jwt: ${jwtToken.error}`,
            );
            await setTokenCache(tokenCacheRedis, `token:${token.sub}`, {
              token: jwtToken,
              timestamp: Date.now(),
            });
            return jwtToken;
          }
        }
      }

      const currentToken = await getTokenCache(
        tokenCacheRedis,
        `token:${token.sub}`,
      );
      console.debug(
        "currentToken from cache",
        JSON.stringify(currentToken, null, 2),
        "will be returned?",
        currentToken &&
          !shouldRefreshToken(currentToken.token.accessTokenExpires),
      );
      if (
        currentToken &&
        !shouldRefreshToken(currentToken.token.accessTokenExpires)
      ) {
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
  const lockKey = `${token.sub}-lock`;

  return redlock
    .using([lockKey], 10000, async () => {
      const cached = await getTokenCache(tokenCacheRedis, `token:${token.sub}`);
      if (cached)
        console.debug(
          "received cached token. to delete?",
          Date.now() - cached.timestamp > TOKEN_CACHE_TTL,
        );
      else console.debug("no cached token received");
      if (cached) {
        if (Date.now() - cached.timestamp > TOKEN_CACHE_TTL) {
          await deleteTokenCache(tokenCacheRedis, `token:${token.sub}`);
        } else if (!shouldRefreshToken(cached.token.accessTokenExpires)) {
          console.debug("returning cached token", cached.token);
          return cached.token;
        }
      }

      const currentToken = cached?.token || (token as JWTWithAccessToken);
      const newToken = await refreshAccessToken(currentToken);

      console.debug("current token during refresh", currentToken);
      console.debug("new token during refresh", newToken);

      if (newToken.error) {
        await deleteTokenCache(tokenCacheRedis, `token:${token.sub}`);
        return newToken;
      }

      assertNotExists(
        newToken.error,
        `panic! trying to cache token with error during refresh: ${newToken.error}`,
      );
      await setTokenCache(tokenCacheRedis, `token:${token.sub}`, {
        token: newToken,
        timestamp: Date.now(),
      });

      return newToken;
    })
    .catch((e) => {
      console.error("error refreshing token", e);
      deleteTokenCache(tokenCacheRedis, `token:${token.sub}`).catch((e) => {
        console.error("error deleting errored token", e);
      });
      return {
        ...token,
        error: REFRESH_ACCESS_TOKEN_ERROR,
      } as JWTWithAccessToken;
    });
}

const AUTHENTIC_REFRESH_TOKEN_URL = assertExistsAndNonEmptyString(
  process.env.AUTHENTIK_REFRESH_TOKEN_URL,
  "AUTHENTIK_REFRESH_TOKEN_URL required",
);

async function refreshAccessToken(token: JWT): Promise<JWTWithAccessToken> {
  try {
    const url = AUTHENTIC_REFRESH_TOKEN_URL;

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
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
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
