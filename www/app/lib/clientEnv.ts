import {
  assertExists,
  assertExistsAndNonEmptyString,
  NonEmptyString,
  parseMaybeNonEmptyString,
  parseNonEmptyString,
} from "./utils";
import { isBuildPhase } from "./next";
import { getNextEnvVar } from "./nextBuild";

export const FEATURE_REQUIRE_LOGIN_ENV_NAME = "FEATURE_REQUIRE_LOGIN" as const;
export const FEATURE_PRIVACY_ENV_NAME = "FEATURE_PRIVACY" as const;
export const FEATURE_BROWSE_ENV_NAME = "FEATURE_BROWSE" as const;
export const FEATURE_SEND_TO_ZULIP_ENV_NAME = "FEATURE_SEND_TO_ZULIP" as const;
export const FEATURE_ROOMS_ENV_NAME = "FEATURE_ROOMS" as const;

const FEATURE_ENV_NAMES = [
  FEATURE_REQUIRE_LOGIN_ENV_NAME,
  FEATURE_PRIVACY_ENV_NAME,
  FEATURE_BROWSE_ENV_NAME,
  FEATURE_SEND_TO_ZULIP_ENV_NAME,
  FEATURE_ROOMS_ENV_NAME,
] as const;

export type FeatureEnvName = (typeof FEATURE_ENV_NAMES)[number];

export type EnvFeaturePartial = {
  [key in FeatureEnvName]: boolean | null;
};

export type AuthProviderType = "authentik" | "credentials" | null;

// CONTRACT: isomorphic with JSON.stringify
export type ClientEnvCommon = EnvFeaturePartial & {
  API_URL: NonEmptyString;
  WEBSOCKET_URL: NonEmptyString | null;
  AUTH_PROVIDER: AuthProviderType;
};

let clientEnv: ClientEnvCommon | null = null;
export const getClientEnvClient = (): ClientEnvCommon => {
  if (typeof window === "undefined") {
    throw new Error(
      "getClientEnv() called during SSR - this should only be called in browser environment",
    );
  }
  if (clientEnv) return clientEnv;
  clientEnv = assertExists(
    JSON.parse(
      assertExistsAndNonEmptyString(
        document.body.dataset.env,
        "document.body.dataset.env is missing",
      ),
    ),
    "document.body.dataset.env is parsed to nullish",
  );
  return clientEnv!;
};

const parseBooleanString = (str: string | undefined): boolean | null => {
  if (str === undefined) return null;
  return str === "true";
};

const parseAuthProvider = (): AuthProviderType => {
  const val = process.env.AUTH_PROVIDER;
  if (val === "authentik" || val === "credentials") return val;
  return null;
};

export const getClientEnvServer = (): ClientEnvCommon => {
  if (typeof window !== "undefined") {
    throw new Error(
      "getClientEnv() not called during SSR - this should only be called in server environment",
    );
  }
  if (clientEnv) return clientEnv;

  const features = FEATURE_ENV_NAMES.reduce((acc, x) => {
    acc[x] = parseBooleanString(process.env[x]);
    return acc;
  }, {} as EnvFeaturePartial);

  if (isBuildPhase) {
    return {
      API_URL: getNextEnvVar("API_URL"),
      WEBSOCKET_URL: parseMaybeNonEmptyString(process.env.WEBSOCKET_URL ?? ""),
      AUTH_PROVIDER: parseAuthProvider(),
      ...features,
    };
  }

  clientEnv = {
    API_URL: getNextEnvVar("API_URL"),
    WEBSOCKET_URL: parseMaybeNonEmptyString(process.env.WEBSOCKET_URL ?? ""),
    AUTH_PROVIDER: parseAuthProvider(),
    ...features,
  };
  return clientEnv;
};

export const getClientEnv =
  typeof window === "undefined" ? getClientEnvServer : getClientEnvClient;
