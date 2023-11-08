import { Configuration } from "../api/runtime";
import { DefaultApi } from "../api/apis/DefaultApi";

import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../[domain]/domainContext";

export default function getApi(protectedPath: boolean): DefaultApi | undefined {
  const accessTokenInfo = useFiefAccessTokenInfo();
  const api_url = useContext(DomainContext).api_url;
  const requireLogin = featureEnabled("requireLogin");
  const [api, setApi] = useState<DefaultApi>();

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (protectedPath && requireLogin && !accessTokenInfo) {
      return;
    }

    const apiConfiguration = new Configuration({
      basePath: api_url,
      accessToken: accessTokenInfo
        ? "Bearer " + accessTokenInfo.access_token
        : undefined,
    });
    setApi(new DefaultApi(apiConfiguration));
  }, [!accessTokenInfo, protectedPath]);

  return api;
}
