import { NextResponse } from "next/server";

export async function GET() {
  const health = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV,
    checks: {
      redis: await checkRedis(),
    },
  };

  const allHealthy = Object.values(health.checks).every((check) => check);

  return NextResponse.json(health, {
    status: allHealthy ? 200 : 503,
  });
}

async function checkRedis(): Promise<boolean> {
  try {
    if (!process.env.KV_URL) {
      return false;
    }

    const { tokenCacheRedis } = await import("../../lib/redisClient");
    const testKey = `health:check:${Date.now()}`;
    await tokenCacheRedis.setex(testKey, 10, "OK");
    const value = await tokenCacheRedis.get(testKey);
    await tokenCacheRedis.del(testKey);

    return value === "OK";
  } catch (error) {
    console.error("Redis health check failed:", error);
    return false;
  }
}
