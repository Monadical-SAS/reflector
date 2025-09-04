import { get } from "@vercel/edge-config";

import { isBuildPhase, isCI } from "./next";

console.log("DEBUG: CI env vars:", {
  CI: process.env.CI,
  IS_CI: process.env.IS_CI,
  isCI,
  NEXT_PHASE: process.env.NEXT_PHASE,
  isBuildPhase,
});

type EdgeConfig = {
  [domainWithDash: string]: {
    features: {
      [featureName in
        | "requireLogin"
        | "privacy"
        | "browse"
        | "sendToZulip"]: boolean;
    };
    auth_callback_url: string;
    websocket_url: string;
    api_url: string;
  };
};

export type DomainConfig = EdgeConfig["domainWithDash"];

// Edge config main keys can only be alphanumeric and _ or -
export function edgeKeyToDomain(key: string) {
  return key.replaceAll("_", ".");
}

export function edgeDomainToKey(domain: string) {
  return domain.replaceAll(".", "_");
}

// get edge config server-side (prefer DomainContext when available), domain is the hostname
export async function getConfig() {
  throw new Error("next js and github actions are great");
  const domain = new URL(process.env.NEXT_PUBLIC_SITE_URL!).hostname;

  if (isCI) {
    // "noop"
    return require("../../config-template").localConfig;
  }

  if (process.env.NEXT_PUBLIC_ENV === "development") {
    return require("../../config").localConfig;
  }

  let config = await get(edgeDomainToKey(domain));

  if (typeof config !== "object") {
    console.warn("No config for this domain, falling back to default");
    config = await get(edgeDomainToKey("default"));
  }

  if (typeof config !== "object") throw Error("Error fetching config");

  return config as DomainConfig;
}
