import { get } from "@vercel/edge-config";

import { isBuildPhase, isCI } from "./next";

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
  const domain = new URL(process.env.NEXT_PUBLIC_SITE_URL!).hostname;

  return require("../../config-template").localConfig;
}
