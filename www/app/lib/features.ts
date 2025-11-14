import {
  FEATURE_BROWSE_ENV_NAME,
  FEATURE_PRIVACY_ENV_NAME,
  FEATURE_REQUIRE_LOGIN_ENV_NAME,
  FEATURE_ROOMS_ENV_NAME,
  FEATURE_SEND_TO_ZULIP_ENV_NAME,
  FeatureEnvName,
  getClientEnv,
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

export const ENV_TO_FEATURE: {
  [k in FeatureEnvName]: FeatureName;
} = {
  FEATURE_REQUIRE_LOGIN: "requireLogin",
  FEATURE_PRIVACY: "privacy",
  FEATURE_BROWSE: "browse",
  FEATURE_SEND_TO_ZULIP: "sendToZulip",
  FEATURE_ROOMS: "rooms",
} as const;

export const FEATURE_TO_ENV: {
  [k in FeatureName]: FeatureEnvName;
} = {
  requireLogin: "FEATURE_REQUIRE_LOGIN",
  privacy: "FEATURE_PRIVACY",
  browse: "FEATURE_BROWSE",
  sendToZulip: "FEATURE_SEND_TO_ZULIP",
  rooms: "FEATURE_ROOMS",
};

const features = getClientEnv();

export const featureEnabled = (featureName: FeatureName): boolean => {
  const isSet = features[FEATURE_TO_ENV[featureName]];
  if (isSet === null) return DEFAULT_FEATURES[featureName];
  return isSet;
};
