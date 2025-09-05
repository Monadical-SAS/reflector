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
import { assertExistsAndNonEmptyString } from "./utils";
import { isCI } from "./next";

const API_URL = !isCI
  ? assertExistsAndNonEmptyString(process.env.NEXT_PUBLIC_API_URL)
  : "http://127.0.0.1:1250";

// Create the base openapi-fetch client with a default URL
// The actual URL will be set via middleware in AuthProvider
export const client = createClient<paths>({
  baseUrl: API_URL,
});

export const $api = createFetchClient<paths>(client);

let currentAuthToken: string | null | undefined = null;

client.use({
  onRequest({ request }) {
    if (currentAuthToken) {
      request.headers.set("Authorization", `Bearer ${currentAuthToken}`);
    }
    // XXX Only set Content-Type if not already set (FormData will set its own boundary)
    // This is a work around for uploading file, we're passing a formdata
    // but the content type was still application/json
    if (
      !request.headers.has("Content-Type") &&
      !(request.body instanceof FormData)
    ) {
      request.headers.set("Content-Type", "application/json");
    }
    return request;
  },
});

// the function contract: lightweight, idempotent
export const configureApiAuth = (token: string | null | undefined) => {
  currentAuthToken = token;
};
