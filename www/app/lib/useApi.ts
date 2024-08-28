import { useSession, signOut } from "next-auth/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../domainContext";
import { OpenApi, DefaultService } from "../api";
import { CustomSession } from "./types";

export default function useApi(): DefaultService | null {
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<OpenApi | null>(null);
  const { data: session } = useSession();
  const customSession = session as CustomSession;
  const accessToken = customSession?.accessToken;

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (customSession?.error === "RefreshAccessTokenError") {
      signOut();
    }
  }, [session]);

  useEffect(() => {
    if (requireLogin && !accessToken) {
      return;
    }

    const openApi = new OpenApi({
      BASE: api_url,
      TOKEN: accessToken,
    });

    setApi(openApi);
  }, [accessToken]);

  return api?.default ?? null;
}
