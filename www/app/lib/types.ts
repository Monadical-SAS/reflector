import { Session } from "next-auth";
import { JWT } from "next-auth/jwt";
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
  user: {
    id?: string;
    name?: string | null;
    email?: string | null;
  };
}

// assumption that JWT is JWTWithAccessToken - not ideal, TODO find a reason we have to do that
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
