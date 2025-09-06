import Redis from "ioredis";
import { isBuildPhase } from "./next";
import Redlock, { ResourceLockedError } from "redlock";

export type RedisClient = Pick<Redis, "get" | "setex" | "del">;
export type RedlockClient = {
  using: <T>(
    keys: string | string[],
    ttl: number,
    cb: () => Promise<T>,
  ) => Promise<T>;
};
const KV_USE_TLS = process.env.KV_USE_TLS
  ? process.env.KV_USE_TLS === "true"
  : undefined;

let redisClient: Redis | null = null;

const getRedisClient = (): RedisClient => {
  if (redisClient) return redisClient;
  const redisUrl = process.env.KV_URL;
  if (!redisUrl) {
    throw new Error("KV_URL environment variable is required");
  }
  redisClient = new Redis(redisUrl, {
    maxRetriesPerRequest: 3,
    ...(KV_USE_TLS === true
      ? {
          tls: {},
        }
      : {}),
  });

  redisClient.on("error", (error) => {
    console.error("Redis error:", error);
  });

  return redisClient;
};

// next.js buildtime usage - we want to isolate next.js "build" time concepts here
const noopClient: RedisClient = (() => {
  const noopSetex: Redis["setex"] = async () => {
    return "OK" as const;
  };
  const noopDel: Redis["del"] = async () => {
    return 0;
  };
  return {
    get: async () => {
      return null;
    },
    setex: noopSetex,
    del: noopDel,
  };
})();

const noopRedlock: RedlockClient = {
  using: <T>(resource: string | string[], ttl: number, cb: () => Promise<T>) =>
    cb(),
};

export const redlock: RedlockClient = isBuildPhase
  ? noopRedlock
  : (() => {
      const r = new Redlock([getRedisClient()], {});
      r.on("error", (error) => {
        if (error instanceof ResourceLockedError) {
          return;
        }

        // Log all other errors.
        console.error(error);
      });
      return r;
    })();

export const tokenCacheRedis = isBuildPhase ? noopClient : getRedisClient();
