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
  requireLogin: false,
  privacy: true,
  browse: false,
  sendToZulip: false,
  rooms: false,
} as const;

function parseBooleanEnv(
  value: string | undefined,
  defaultValue: boolean = false,
): boolean {
  if (!value) return defaultValue;
  return value.toLowerCase() === "true";
}

// WARNING: keep process.env.* as-is, next.js won't see them if you generate dynamically
const features: Features = {
  requireLogin: parseBooleanEnv(
    process.env.NEXT_PUBLIC_FEATURE_REQUIRE_LOGIN,
    DEFAULT_FEATURES.requireLogin,
  ),
  privacy: parseBooleanEnv(
    process.env.NEXT_PUBLIC_FEATURE_PRIVACY,
    DEFAULT_FEATURES.privacy,
  ),
  browse: parseBooleanEnv(
    process.env.NEXT_PUBLIC_FEATURE_BROWSE,
    DEFAULT_FEATURES.browse,
  ),
  sendToZulip: parseBooleanEnv(
    process.env.NEXT_PUBLIC_FEATURE_SEND_TO_ZULIP,
    DEFAULT_FEATURES.sendToZulip,
  ),
  rooms: parseBooleanEnv(
    process.env.NEXT_PUBLIC_FEATURE_ROOMS,
    DEFAULT_FEATURES.rooms,
  ),
};

export const featureEnabled = (featureName: FeatureName): boolean => {
  return features[featureName];
};
