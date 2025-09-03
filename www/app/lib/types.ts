import type { Session } from "next-auth";
import type { JWT } from "next-auth/jwt";
import { parseMaybeNonEmptyString } from "./utils";

export interface JWTWithAccessToken extends JWT {
  accessToken: string;
  accessTokenExpires: number;
  refreshToken: string;
  error?: string;
}

export interface CustomSession extends Session {
  accessToken: string;
  accessTokenExpires: number;
  error?: string;
  user: Session["user"] & {
    id: string;
  };
}

// assumption that JWT is JWTWithAccessToken - we set it in jwt callback of auth; typing isn't strong around there
// but the assumption is crucial to auth working
export const assertExtendedToken = <T>(
  t: T,
): T & {
  accessTokenExpires: number;
  accessToken: string;
} => {
  if (
    typeof (t as { accessTokenExpires: any }).accessTokenExpires === "number" &&
    !isNaN((t as { accessTokenExpires: any }).accessTokenExpires) &&
    typeof (
      t as {
        accessToken: any;
      }
    ).accessToken === "string" &&
    parseMaybeNonEmptyString((t as { accessToken: any }).accessToken) !== null
  ) {
    return t as T & {
      accessTokenExpires: number;
      accessToken: string;
    };
  }
  throw new Error("Token is not extended with access token");
};

export const assertExtendedTokenAndUserId = <U, T extends { user?: U }>(
  t: T,
): T & {
  accessTokenExpires: number;
  accessToken: string;
  user: U & {
    id: string;
  };
} => {
  const extendedToken = assertExtendedToken(t);
  if (typeof (extendedToken.user as any)?.id === "string") {
    return t as T & {
      accessTokenExpires: number;
      accessToken: string;
      user: U & {
        id: string;
      };
    };
  }
  throw new Error("Token is not extended with user id");
};
