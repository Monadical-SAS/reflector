import { z } from "zod";
import { REFRESH_ACCESS_TOKEN_BEFORE } from "./auth";

const TokenCacheEntrySchema = z.object({
  token: z.object({
    sub: z.string().optional(),
    name: z.string().nullish(),
    email: z.string().nullish(),
    accessToken: z.string(),
    accessTokenExpires: z.number(),
    refreshToken: z.string().optional(),
  }),
  timestamp: z.number(),
});

const TokenCacheEntryCodec = z.codec(z.string(), TokenCacheEntrySchema, {
  decode: (jsonString) => {
    const parsed = JSON.parse(jsonString);
    return TokenCacheEntrySchema.parse(parsed);
  },
  encode: (value) => JSON.stringify(value),
});

export type TokenCacheEntry = z.infer<typeof TokenCacheEntrySchema>;

export type KV = {
  get(key: string): Promise<string | null>;
  setex(key: string, seconds: number, value: string): Promise<"OK">;
  del(key: string): Promise<number>;
};

export async function getTokenCache(
  redis: KV,
  key: string,
): Promise<TokenCacheEntry | null> {
  const data = await redis.get(key);
  if (!data) return null;

  try {
    return TokenCacheEntryCodec.decode(data);
  } catch (error) {
    console.error("Invalid token cache data:", error);
    await redis.del(key);
    return null;
  }
}

const TTL_SECONDS = 30 * 24 * 60 * 60;

export async function setTokenCache(
  redis: KV,
  key: string,
  value: TokenCacheEntry,
): Promise<void> {
  const encodedValue = TokenCacheEntryCodec.encode(value);
  await redis.setex(key, TTL_SECONDS, encodedValue);
}

export async function deleteTokenCache(redis: KV, key: string): Promise<void> {
  await redis.del(key);
}
