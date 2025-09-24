import {
  FEATURE_BROWSE_ENV_NAME,
  FEATURE_PRIVACY_ENV_NAME,
  FEATURE_REQUIRE_LOGIN_ENV_NAME,
  FEATURE_ROOMS_ENV_NAME,
  FEATURE_SEND_TO_ZULIP_ENV_NAME,
} from "./clientEnv";

export const FEATURES = [
  "requireLogin",
  "privacy",
  "browse",
  "sendToZulip",
  "rooms",
] as const;

export type FeatureName = (typeof FEATURES)[number];

export type Features = Readonly<Record<FeatureName, boolean>>;

export const DEFAULT_FEATURES: Features = {
  requireLogin: true,
  privacy: true,
  browse: true,
  sendToZulip: true,
  rooms: true,
} as const;

function parseBooleanEnv(
  value: string | undefined,
  defaultValue: boolean = false,
): boolean {
  if (!value) return defaultValue;
  return value.toLowerCase() === "true";
}

const features: Features = {
  requireLogin: parseBooleanEnv(
    process.env[FEATURE_REQUIRE_LOGIN_ENV_NAME],
    DEFAULT_FEATURES.requireLogin,
  ),
  privacy: parseBooleanEnv(
    process.env[FEATURE_PRIVACY_ENV_NAME],
    DEFAULT_FEATURES.privacy,
  ),
  browse: parseBooleanEnv(
    process.env[FEATURE_BROWSE_ENV_NAME],
    DEFAULT_FEATURES.browse,
  ),
  sendToZulip: parseBooleanEnv(
    process.env[FEATURE_SEND_TO_ZULIP_ENV_NAME],
    DEFAULT_FEATURES.sendToZulip,
  ),
  rooms: parseBooleanEnv(
    process.env[FEATURE_ROOMS_ENV_NAME],
    DEFAULT_FEATURES.rooms,
  ),
};

export const featureEnabled = (featureName: FeatureName): boolean => {
  return features[featureName];
};
