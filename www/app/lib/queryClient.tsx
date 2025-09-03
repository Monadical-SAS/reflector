"use client";

import { QueryClient } from "@tanstack/react-query";
import { broadcastQueryClient } from "@tanstack/query-broadcast-client-experimental";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

broadcastQueryClient({
  queryClient,
  broadcastChannel: "reflector-query-client",
});
