import { Session } from "next-auth";
import { JWT } from "next-auth/jwt";

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
