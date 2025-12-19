import { assertExistsAndNonEmptyString } from "./utils";

export const REFRESH_ACCESS_TOKEN_ERROR = "RefreshAccessTokenError" as const;
// 4 min is 1 min less than default authentic value. here we assume that authentic won't be set to access tokens < 4 min
export const REFRESH_ACCESS_TOKEN_BEFORE = 4 * 60 * 1000;

export const shouldRefreshToken = (accessTokenExpires: number): boolean => {
  const timeLeft = accessTokenExpires - Date.now();
  return timeLeft < REFRESH_ACCESS_TOKEN_BEFORE;
};

export const LOGIN_REQUIRED_PAGES = [
  "/transcripts/[!new]",
  "/browse(.*)",
  "/rooms(.*)",
];

export const PROTECTED_PAGES = new RegExp(
  LOGIN_REQUIRED_PAGES.map((page) => `^${page}$`).join("|"),
);

export function getLogoutRedirectUrl(pathname: string): string {
  const transcriptPagePattern = /^\/transcripts\/[^/]+$/;
  return transcriptPagePattern.test(pathname) ? pathname : "/";
}
