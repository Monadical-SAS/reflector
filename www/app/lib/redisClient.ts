import Redis from "ioredis";
import { isBuildPhase } from "./next";

export type RedisClient = Pick<Redis, "get" | "setex" | "del">;

const getRedisClient = (): RedisClient => {
  const redisUrl = process.env.KV_URL;
  if (!redisUrl) {
    throw new Error("KV_URL environment variable is required");
  }
  const redis = new Redis(redisUrl, {
    maxRetriesPerRequest: 3,
    lazyConnect: true,
  });

  redis.on("error", (error) => {
    console.error("Redis error:", error);
  });

  // not necessary but will indicate redis config errors by failfast at startup
  // happens only once; after that connection is allowed to die and the lib is assumed to be able to restore it eventually
  redis.connect().catch((e) => {
    console.error("Failed to connect to Redis:", e);
    process.exit(1);
  });

  return redis;
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
export const tokenCacheRedis = isBuildPhase ? noopClient : getRedisClient();
