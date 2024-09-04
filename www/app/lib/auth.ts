// import { kv } from "@vercel/kv";
import Redlock, { ResourceLockedError } from "redlock";
import { AuthOptions } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import { JWT } from "next-auth/jwt";
import { JWTWithAccessToken, CustomSession } from "./types";
import Redis from "ioredis";

const PRETIMEOUT = 60; // seconds before token expires to refresh it
const DEFAULT_REDIS_KEY_TIMEOUT = 60 * 60 * 24 * 30; // 30 days (refresh token expires in 30 days)
const kv = new Redis(process.env.KV_URL || "", {
  tls: {},
});
const redlock = new Redlock([kv], {});

redlock.on("error", (error) => {
  if (error instanceof ResourceLockedError) {
    return;
  }

  // Log all other errors.
  console.error(error);
});

export const authOptions: AuthOptions = {
  providers: [
    AuthentikProvider({
      clientId: process.env.AUTHENTIK_CLIENT_ID as string,
      clientSecret: process.env.AUTHENTIK_CLIENT_SECRET as string,
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
      const extendedToken = token as JWTWithAccessToken;
      if (account && user) {
        // called only on first login
        // XXX account.expires_in used in example is not defined for authentik backend, but expires_at is
        const expiresAt = (account.expires_at as number) - PRETIMEOUT;
        const jwtToken = {
          ...extendedToken,
          accessToken: account.access_token,
          accessTokenExpires: expiresAt * 1000,
          refreshToken: account.refresh_token,
        };
        kv.set(
          `token:${jwtToken.sub}`,
          JSON.stringify(jwtToken),
          "EX",
          DEFAULT_REDIS_KEY_TIMEOUT,
        );
        return jwtToken;
      }

      if (Date.now() < extendedToken.accessTokenExpires) {
        return token;
      }

      // access token has expired, try to update it
      return await redisLockedrefreshAccessToken(token);
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

async function redisLockedrefreshAccessToken(token: JWT) {
  return await redlock.using(
    [token.sub as string, "jwt-refresh"],
    5000,
    async () => {
      const redisToken = await kv.get(`token:${token.sub}`);
      const currentToken = JSON.parse(
        redisToken as string,
      ) as JWTWithAccessToken;

      // if there is multiple requests for the same token, it may already have been refreshed
      if (Date.now() < currentToken.accessTokenExpires) {
        return currentToken;
      }

      // now really do the request
      const newToken = await refreshAccessToken(currentToken);
      await kv.set(
        `token:${currentToken.sub}`,
        JSON.stringify(newToken),
        "EX",
        DEFAULT_REDIS_KEY_TIMEOUT,
      );
      return newToken;
    },
  );
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
