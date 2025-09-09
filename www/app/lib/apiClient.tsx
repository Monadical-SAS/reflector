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

const waitForAuthTokenDefinitivePresenceOrAbscence = async () => {
  let tries = 0;
  let time = 0;
  const STEP = 100;
  while (currentAuthToken === undefined) {
    await new Promise((resolve) => setTimeout(resolve, STEP));
    time += STEP;
    tries++;
    // most likely first try is more than enough, if it's more there's already something weird happens
    if (tries > 10) {
      // even when there's no auth assumed at all, we probably should explicitly call configureApiAuth(null)
      throw new Error(
        `Could not get auth token definitive presence/absence in ${time}ms. not calling configureApiAuth?`,
      );
    }
  }
};

client.use({
  async onRequest({ request }) {
    await waitForAuthTokenDefinitivePresenceOrAbscence();
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

let currentAuthToken: string | null | undefined = undefined;

// the function contract: lightweight, idempotent
export const configureApiAuth = (token: string | null) => {
  currentAuthToken = token;
};
