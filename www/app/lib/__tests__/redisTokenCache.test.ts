import {
  getTokenCache,
  setTokenCache,
  deleteTokenCache,
  TokenCacheEntry,
  KV,
} from "../redisTokenCache";

const mockKV: KV & {
  clear: () => void;
} = (() => {
  const data = new Map<string, string>();
  return {
    async get(key: string): Promise<string | null> {
      return data.get(key) || null;
    },

    async setex(key: string, seconds_: number, value: string): Promise<"OK"> {
      data.set(key, value);
      return "OK";
    },

    async del(key: string): Promise<number> {
      const existed = data.has(key);
      data.delete(key);
      return existed ? 1 : 0;
    },

    clear() {
      data.clear();
    },
  };
})();

describe("Redis Token Cache", () => {
  beforeEach(() => {
    mockKV.clear();
  });

  test("basic write/read - value written equals value read", async () => {
    const testKey = "token:test-user-123";
    const testValue: TokenCacheEntry = {
      token: {
        sub: "test-user-123",
        name: "Test User",
        email: "test@example.com",
        accessToken: "access-token-123",
        accessTokenExpires: Date.now() + 3600000, // 1 hour from now
        refreshToken: "refresh-token-456",
      },
      timestamp: Date.now(),
    };

    await setTokenCache(mockKV, testKey, testValue);
    const retrievedValue = await getTokenCache(mockKV, testKey);

    expect(retrievedValue).not.toBeNull();
    expect(retrievedValue).toEqual(testValue);
    expect(retrievedValue?.token.accessToken).toBe(testValue.token.accessToken);
    expect(retrievedValue?.token.sub).toBe(testValue.token.sub);
    expect(retrievedValue?.timestamp).toBe(testValue.timestamp);
  });

  test("get returns null for non-existent key", async () => {
    const result = await getTokenCache(mockKV, "non-existent-key");
    expect(result).toBeNull();
  });

  test("delete removes token from cache", async () => {
    const testKey = "token:delete-test";
    const testValue: TokenCacheEntry = {
      token: {
        accessToken: "test-token",
        accessTokenExpires: Date.now() + 3600000,
      },
      timestamp: Date.now(),
    };

    await setTokenCache(mockKV, testKey, testValue);
    await deleteTokenCache(mockKV, testKey);

    const result = await getTokenCache(mockKV, testKey);
    expect(result).toBeNull();
  });
});
