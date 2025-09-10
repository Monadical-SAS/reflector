import { DEFAULT_FEATURES, FeatureName, FEATURES, Features } from "./features";
import {
  assertExistsAndNonEmptyString,
  NonEmptyString,
  parseNonEmptyString,
} from "./utils";
import { Mutable } from "./types";

type Config = Readonly<{
  features: Features;
  auth_callback_url: string;
  websocket_url: string;
  api_url: string;
}>;

function parseBooleanEnv(
  value: string | undefined,
  defaultValue: boolean = false,
): boolean {
  if (!value) return defaultValue;
  return value.toLowerCase() === "true";
}

/**
 * Converts a camelCase feature name to its corresponding environment variable name.
 *
 * @example
 * getFeatureEnvVarName('requireLogin') // returns 'NEXT_PUBLIC_FEATURE_REQUIRE_LOGIN'
 * getFeatureEnvVarName('sendToZulip') // returns 'NEXT_PUBLIC_FEATURE_SEND_TO_ZULIP'
 * getFeatureEnvVarName('privacy') // returns 'NEXT_PUBLIC_FEATURE_PRIVACY'
 *
 * @param featureName - The camelCase feature name
 * @returns The SCREAMING_SNAKE_CASE environment variable name
 */
export function getFeatureEnvVarName(featureName: FeatureName): NonEmptyString {
  // Convert camelCase to SCREAMING_SNAKE_CASE
  const screamingSnakeCase = featureName
    .replace(/([a-z])([A-Z])/g, "$1_$2")
    .toUpperCase();
  return parseNonEmptyString(`NEXT_PUBLIC_FEATURE_${screamingSnakeCase}`);
}

let config: Config | null = null;
export function getConfig(): Config {
  if (config !== null) return config;
  const features = FEATURES.reduce<Mutable<Features>>((acc, featureName) => {
    const envVarName = getFeatureEnvVarName(featureName);
    const defaultValue = DEFAULT_FEATURES[featureName];
    acc[featureName] = parseBooleanEnv(process.env[envVarName], defaultValue);
    return acc;
  }, {} as Mutable<Features>);
  config = {
    features,
    api_url: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:1250",
    websocket_url:
      process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://127.0.0.1:1250",
    auth_callback_url:
      process.env.NEXT_PUBLIC_AUTH_CALLBACK_URL ||
      `${assertExistsAndNonEmptyString(process.env.NEXT_PUBLIC_SITE_URL)}/auth-callback`,
  };
  return getConfig();
}

export const featureEnabled = (featureName: FeatureName): boolean => {
  return getConfig().features[featureName];
};
