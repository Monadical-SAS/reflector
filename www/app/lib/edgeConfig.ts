import { get } from "@vercel/edge-config";

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
  return key.replaceAll(".", "_");
}

export function edgeDomainToKey(domain: string) {
  return domain.replaceAll("_", ".");
}

// get edge config server-side (prefer DomainContext when available), domain is the hostname
export async function getConfig(domain: string) {
  const config = await get(edgeDomainToKey(domain));

  if (typeof config !== "object") throw Error("Error fetchig config");

  return config as DomainConfig;
}
