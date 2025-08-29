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

// Create the base openapi-fetch client with a default URL
// The actual URL will be set via middleware in ApiAuthProvider
export const client = createClient<paths>({
  baseUrl: "http://127.0.0.1:1250",
});

// Create the React Query client wrapper
export const $api = createFetchClient<paths>(client);

// Store the current auth token
let currentAuthToken: string | null | undefined = null;

// Set up authentication middleware once
client.use({
  onRequest({ request }) {
    if (currentAuthToken) {
      request.headers.set("Authorization", `Bearer ${currentAuthToken}`);
    }
    // Only set Content-Type if not already set (FormData will set its own boundary)
    if (
      !request.headers.has("Content-Type") &&
      !(request.body instanceof FormData)
    ) {
      request.headers.set("Content-Type", "application/json");
    }
    return request;
  },
});

// Configure authentication by updating the token
export const configureApiAuth = (token: string | null | undefined) => {
  currentAuthToken = token;
};

// Export typed hooks for convenience
export const useApiQuery = $api.useQuery;
export const useApiMutation = $api.useMutation;
export const useApiSuspenseQuery = $api.useSuspenseQuery;
