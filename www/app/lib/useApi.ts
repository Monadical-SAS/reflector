import { useSession, signOut } from "next-auth/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../domainContext";
import { OpenApi, DefaultService } from "../api";

export default function useApi(): DefaultService | null {
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<OpenApi | null>(null);
  const { data: session } = useSession({ required: !!requireLogin });
  const accessTokenInfo = session?.accessToken;

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (session?.error === "RefreshAccessTokenError") {
      signOut();
    }
  }, [session]);

  useEffect(() => {
    if (requireLogin && !accessTokenInfo) {
      return;
    }

    const openApi = new OpenApi({
      BASE: api_url,
      TOKEN: accessTokenInfo,
    });

    setApi(openApi);
  }, [!accessTokenInfo]);

  return api?.default ?? null;
}
