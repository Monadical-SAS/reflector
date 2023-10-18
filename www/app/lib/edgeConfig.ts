import { get } from "@vercel/edge-config";
import { isDevelopment } from "./utils";

const localConfig = {
  features: {
    requireLogin: true,
    privacy: true,
    browse: true,
  },
  api_url: "http://127.0.0.1:1250",
  auth_callback_url: "http://localhost:3000/auth-callback",
};

type EdgeConfig = {
  [domainWithDash: string]: {
    features: {
      [featureName in "requireLogin" | "privacy" | "browse"]: boolean;
    };
    auth_callback_url: string;
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
export async function getConfig(domain: string) {
  if (isDevelopment()) {
    return localConfig;
  }

  let config = await get(edgeDomainToKey(domain));

  if (typeof config !== "object") {
    console.warn("No config for this domain, falling back to default");
    config = await get(edgeDomainToKey("default"));
  }

  if (typeof config !== "object") throw Error("Error fetching config");

  return config as DomainConfig;
}
