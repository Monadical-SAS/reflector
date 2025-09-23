"use client";

import createClient from "openapi-fetch";
import type { paths } from "../reflector-api";
import createFetchClient from "openapi-react-query";
import { assertExistsAndNonEmptyString, parseNonEmptyString } from "./utils";
import { isBuildPhase } from "./next";
import { getSession } from "next-auth/react";
import { assertExtendedToken } from "./types";
import { getClientEnv } from "./clientEnv";

export const API_URL = !isBuildPhase
  ? getClientEnv().API_URL
  : "http://localhost";

// TODO decide strict validation or not
export const WEBSOCKET_URL =
  getClientEnv().WEBSOCKET_URL || "ws://127.0.0.1:1250";

export const client = createClient<paths>({
  baseUrl: API_URL,
});

// will assert presence/absence of login initially
const initialSessionPromise = getSession();

const waitForAuthTokenDefinitivePresenceOrAbsence = async () => {
  const initialSession = await initialSessionPromise;
  if (currentAuthToken === undefined) {
    currentAuthToken =
      initialSession === null
        ? null
        : assertExtendedToken(initialSession).accessToken;
  }
  // otherwise already overwritten by external forces
  return currentAuthToken;
};

client.use({
  async onRequest({ request }) {
    const token = await waitForAuthTokenDefinitivePresenceOrAbsence();
    if (token !== null) {
      request.headers.set(
        "Authorization",
        `Bearer ${parseNonEmptyString(token)}`,
      );
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
export const configureApiAuth = (token: string | null | undefined) => {
  // watch only for the initial loading; "reloading" state assumes token presence/absence
  if (token === undefined && currentAuthToken !== undefined) return;
  currentAuthToken = token;
};
