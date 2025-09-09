"use client";

import createClient from "openapi-fetch";
import type { paths } from "../reflector-api";
import createFetchClient from "openapi-react-query";
import { assertExistsAndNonEmptyString } from "./utils";
import { isBuildPhase } from "./next";

const API_URL = !isBuildPhase
  ? assertExistsAndNonEmptyString(process.env.NEXT_PUBLIC_API_URL)
  : "http://localhost";

export const client = createClient<paths>({
  baseUrl: API_URL,
});

// has to be called BEFORE $api is created with createFetchClient<paths>(client) or onRequest doesn't fire [at least for POST]
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

export const $api = createFetchClient<paths>(client);

let currentAuthToken: string | null | undefined = null;

// the function contract: lightweight, idempotent
export const configureApiAuth = (token: string | null | undefined) => {
  currentAuthToken = token;
};
