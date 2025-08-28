"use client";

import createClient from "openapi-fetch";
import type { paths } from "../reflector-api";
import {
  queryOptions,
  useMutation,
  useQuery,
  useSuspenseQuery,
} from "@tanstack/react-query";
import createFetchClient from "openapi-react-query";

// Create the base openapi-fetch client
export const client = createClient<paths>({
  // Base URL will be set dynamically via middleware
  baseUrl: "",
  headers: {
    "Content-Type": "application/json",
  },
});

// Create the React Query client wrapper
export const $api = createFetchClient<paths>(client);

// Configure authentication
export const configureApiAuth = (token: string | null | undefined) => {
  if (token) {
    client.use({
      onRequest({ request }) {
        request.headers.set("Authorization", `Bearer ${token}`);
        return request;
      },
    });
  }
};

// Export typed hooks for convenience
export const useApiQuery = $api.useQuery;
export const useApiMutation = $api.useMutation;
export const useApiSuspenseQuery = $api.useSuspenseQuery;
