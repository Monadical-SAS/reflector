import { Configuration } from "../api/runtime";
import { DefaultApi } from "../api/apis/DefaultApi";

import { useFiefAccessTokenInfo } from "@fief/fief/nextjs/react";

export default function getApi(): DefaultApi {
  const accessTokenInfo = useFiefAccessTokenInfo();

  const apiConfiguration = new Configuration({
    basePath: process.env.NEXT_PUBLIC_API_URL,
    accessToken: accessTokenInfo
      ? "Bearer " + accessTokenInfo.access_token
      : undefined,
  });
  const api = new DefaultApi(apiConfiguration);

  return api;
}
