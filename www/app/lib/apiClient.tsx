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
import { isBuildPhase } from "./next";
import { Session } from "next-auth";
import { assertCustomSession } from "./types";
import { HttpMethod, PathsWithMethod } from "openapi-typescript-helpers";

const API_URL = !isBuildPhase
  ? assertExistsAndNonEmptyString(process.env.NEXT_PUBLIC_API_URL)
  : "http://localhost";

// Create the base openapi-fetch client with a default URL
// The actual URL will be set via middleware in AuthProvider
export const client = createClient<paths>({
  baseUrl: API_URL,
});

export const $api = createFetchClient<paths>(client);

let currentAuthToken: string | null | undefined = null;
let refreshAuthCallback: (() => Promise<Session | null>) | null = null;

const injectAuth = (request: Request, accessToken: string | null) => {
  if (accessToken) {
    request.headers.set("Authorization", `Bearer ${currentAuthToken}`);
  } else {
    request.headers.delete("Authorization");
  }
  return request;
};

client.use({
  onRequest({ request }) {
    request = injectAuth(request, currentAuthToken || null);
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

client.use({
  async onResponse({ response, request, params, schemaPath }) {
    if (response.status === 401) {
      console.log(
        "response.status is 401!",
        refreshAuthCallback,
        request,
        schemaPath,
      );
    }
    if (response.status === 401 && refreshAuthCallback) {
      try {
        const session = await refreshAuthCallback();
        if (!session) {
          console.warn("Token refresh failed, no session returned");
          return response;
        }
        const customSession = assertCustomSession(session);
        currentAuthToken = customSession.accessToken;
        const r = await client.request(
          request.method as HttpMethod,
          schemaPath as PathsWithMethod<paths, HttpMethod>,
          ...params,
        );
        return r.response;
      } catch (error) {
        console.error("Token refresh failed during 401 retry:", error);
      }
    }
    return response;
  },
});

// the function contract: lightweight, idempotent
export const configureApiAuth = (token: string | null | undefined) => {
  currentAuthToken = token;
};

export const configureApiAuthRefresh = (
  callback: (() => Promise<Session | null>) | null,
) => {
  refreshAuthCallback = callback;
};
