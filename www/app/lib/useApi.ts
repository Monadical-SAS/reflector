import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../[domain]/domainContext";
import { CookieContext } from "../(auth)/fiefWrapper";
import { OpenApi, DefaultService } from "../api";

export default function useApi(): DefaultService | null {
  const accessTokenInfo = useFiefAccessTokenInfo();
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<OpenApi | null>(null);
  const { hasAuthCookie } = useContext(CookieContext);

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (hasAuthCookie && requireLogin && !accessTokenInfo) {
      return;
    }

    if (!accessTokenInfo) return;

    const openApi = new OpenApi({
      BASE: api_url,
      TOKEN: accessTokenInfo?.access_token,
    });

    setApi(openApi);
  }, [!accessTokenInfo, hasAuthCookie]);

  return api?.default ?? null;
}
