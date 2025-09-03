export const REFRESH_ACCESS_TOKEN_ERROR = "RefreshAccessTokenError" as const;
// 4 min is 1 min less than default authentic value. here we assume that authentic won't be set to access tokens < 4 min
export const REFRESH_ACCESS_TOKEN_BEFORE = 4 * 60 * 1000;
