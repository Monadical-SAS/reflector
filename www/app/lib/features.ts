import { getClientEnv } from "./clientEnv";

export const FEATURE_ENV_NAMES = [
  "FEATURE_REQUIRE_LOGIN",
  "FEATURE_PRIVACY",
  "FEATURE_BROWSE",
  "FEATURE_SEND_TO_ZULIP",
  "FEATURE_ROOMS",
] as const;

export type FeatureEnvName = (typeof FEATURE_ENV_NAMES)[number];

// CONTRACT: isomorphic with JSON.stringify
export type EnvFeaturePartial = {
  [f in FeatureEnvName]: boolean | null;
};

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

export const featureEnabled = (featureName: FeatureName): boolean => {
  const features = getClientEnv();
  return features[FEATURE_TO_ENV[featureName]] || DEFAULT_FEATURES[featureName];
};
