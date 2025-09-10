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
