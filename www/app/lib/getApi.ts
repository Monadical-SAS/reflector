import { Configuration } from "../api/runtime";
import { DefaultApi } from "../api/apis/DefaultApi";

import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";
import { useContext } from "react";
import { DomainContext } from "../[domain]/domainContext";

export default function getApi(): DefaultApi {
  const accessTokenInfo = useFiefAccessTokenInfo();
  const api_url = useContext(DomainContext).api_url;
  if (!api_url) throw new Error("no API URL");

  const apiConfiguration = new Configuration({
    basePath: api_url,
    accessToken: accessTokenInfo
      ? "Bearer " + accessTokenInfo.access_token
      : undefined,
  });
  const api = new DefaultApi(apiConfiguration);

  return api;
}
