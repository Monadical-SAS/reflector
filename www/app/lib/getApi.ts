import { DefaultService, OpenAPI } from "../api";

import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../[domain]/domainContext";
import { CookieContext } from "../(auth)/fiefWrapper";

export default function getApi(): DefaultService | undefined {
  const accessTokenInfo = useFiefAccessTokenInfo();
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<DefaultService>();
  const { hasAuthCookie } = useContext(CookieContext);

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (hasAuthCookie && requireLogin && !accessTokenInfo) {
      return;
    }

    // const apiConfiguration = new Configuration({
    //   basePath: api_url,
    //   accessToken: accessTokenInfo
    //     ? "Bearer " + accessTokenInfo.access_token
    //     : undefined,
    // });
    OpenAPI.BASE = api_url;
    if (accessTokenInfo) {
      OpenAPI.TOKEN = "Bearer " + accessTokenInfo.access_token;
    }
    setApi(DefaultService);
  }, [!accessTokenInfo, hasAuthCookie]);

  return api;
}
