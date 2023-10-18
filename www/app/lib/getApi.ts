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
    // console.log('trying auth', protectedPath, requireLogin, accessTokenInfo)
    if (protectedPath && requireLogin && !accessTokenInfo) {
      // console.log('waiting auth')
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
