// NextAuth route handler for Authentik
// Refresh rotation has been taken from https://next-auth.js.org/v3/tutorials/refresh-token-rotation even if we are using 4.x

import NextAuth from "next-auth";
import { AuthOptions, Session } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import { JWT } from "next-auth/jwt";
import { JWTWithAccessToken, CustomSession } from "../../../lib/types";

const PRETIMEOUT = 60; // seconds before token expires to refresh it

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
  // pages: {
  //   signIn: "/login",
  // },
  callbacks: {
    async jwt({ token, account, user }) {
      const extendedToken = token as JWTWithAccessToken;
      if (account && user) {
        // called only on first login
        // XXX account.expires_in used in example is not defined for authentik backend, but expires_at is
        const expiresAt = (account.expires_at as number) - PRETIMEOUT;

        return {
          ...extendedToken,
          accessToken: account.access_token,
          accessTokenExpires: expiresAt * 1000,
          refreshToken: account.refresh_token,
        };
      }

      if (Date.now() < extendedToken.accessTokenExpires) {
        return token;
      }

      // access token has expired, try to update it
      return await refreshAccessToken(token);
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

async function refreshAccessToken(token: JWT) {
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
    };
  }
}

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
