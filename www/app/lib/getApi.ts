import { Configuration } from "../api/runtime";
import { DefaultApi } from "../api/apis/DefaultApi";

import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../[domain]/domainContext";
import { CookieContext } from "../(auth)/fiefWrapper";

export default function getApi(): DefaultApi | undefined {
  const accessTokenInfo = useFiefAccessTokenInfo();
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<DefaultApi>();
  const { hasAuthCookie } = useContext(CookieContext);

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (hasAuthCookie && requireLogin && !accessTokenInfo) {
      return;
    }

    const apiConfiguration = new Configuration({
      basePath: api_url,
      accessToken: accessTokenInfo
        ? "Bearer " + accessTokenInfo.access_token
        : undefined,
    });
    setApi(new DefaultApi(apiConfiguration));
  }, [!accessTokenInfo, hasAuthCookie]);

  return api;
}
