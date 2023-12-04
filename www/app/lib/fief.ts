import { Fief, FiefUserInfo } from "@fief/fief";
import { FiefAuth, IUserInfoCache } from "@fief/fief/nextjs";
import { getConfig } from "./edgeConfig";

export const SESSION_COOKIE_NAME = "reflector-auth";

export const fiefClient = new Fief({
  baseURL: process.env.FIEF_URL ?? "",
  clientId: process.env.FIEF_CLIENT_ID ?? "",
  clientSecret: process.env.FIEF_CLIENT_SECRET ?? "",
});

class MemoryUserInfoCache implements IUserInfoCache {
  private storage: Record<string, any>;

  constructor() {
    this.storage = {};
  }

  async get(id: string): Promise<FiefUserInfo | null> {
    const userinfo = this.storage[id];
    if (userinfo) {
      return userinfo;
    }
    return null;
  }

  async set(id: string, userinfo: FiefUserInfo): Promise<void> {
    this.storage[id] = userinfo;
  }

  async remove(id: string): Promise<void> {
    this.storage[id] = undefined;
  }

  async clear(): Promise<void> {
    this.storage = {};
  }
}

const FIEF_AUTHS = {} as { [domain: string]: FiefAuth };

export const getFiefAuth = async (url: URL) => {
  if (FIEF_AUTHS[url.hostname]) {
    return FIEF_AUTHS[url.hostname];
  } else {
    const config = url && (await getConfig(url.hostname));
    if (config) {
      FIEF_AUTHS[url.hostname] = new FiefAuth({
        client: fiefClient,
        sessionCookieName: SESSION_COOKIE_NAME,
        redirectURI: config.auth_callback_url,
        logoutRedirectURI: url.origin,
        userInfoCache: new MemoryUserInfoCache(),
      });
      return FIEF_AUTHS[url.hostname];
    } else {
      throw new Error("Fief intanciation failed");
    }
  }
};

export const getFiefAuthMiddleware = async (url) => {
  const protectedPaths = [
    {
      matcher: "/transcripts",
      parameters: {},
    },
    {
      matcher: "/browse",
      parameters: {},
    },
  ];
  return (await getFiefAuth(url))?.middleware(protectedPaths);
};
