import { EnvFeaturePartial, FEATURE_ENV_NAMES } from "./features";
import {
  assertExists,
  assertExistsAndNonEmptyString,
  NonEmptyString,
} from "./utils";

// CONTRACT: isomorphic with JSON.stringify
export type ClientEnvCommon = EnvFeaturePartial & {
  API_URL: NonEmptyString;
  WEBSOCKET_URL: NonEmptyString | null;
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

const parseBooleanString = (str: string | undefined): boolean => {
  return str === "true";
};

export const getClientEnvServer = (): ClientEnvCommon => {
  if (typeof window !== "undefined") {
    throw new Error(
      "getClientEnv() not called during SSR - this should only be called in server environment",
    );
  }
  if (clientEnv) return clientEnv;
  clientEnv = {
    API_URL: assertExistsAndNonEmptyString(
      process.env.API_URL,
      "API_URL is missing",
    ),
    WEBSOCKET_URL: assertExistsAndNonEmptyString(
      process.env.WEBSOCKET_URL,
      "WEBSOCKET_URL is missing",
    ),
    ...FEATURE_ENV_NAMES.reduce((acc, x) => {
      acc[x] = parseBooleanString(process.env[x]);
      return acc;
    }, {} as EnvFeaturePartial),
  };
  return clientEnv;
};

export const getClientEnv =
  typeof window === "undefined" ? getClientEnvServer : getClientEnvClient;
