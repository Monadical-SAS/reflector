"use client";

import { useEffect, useContext } from "react";
import { client, configureApiAuth } from "./apiClient";
import useSessionAccessToken from "./useSessionAccessToken";
import { DomainContext } from "../domainContext";

export function ApiAuthProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useSessionAccessToken();
  const { api_url } = useContext(DomainContext);

  useEffect(() => {
    // Configure base URL
    if (api_url) {
      client.use({
        onRequest({ request }) {
          // Update the base URL for all requests
          const url = new URL(request.url);
          const apiUrl = new URL(api_url);
          url.protocol = apiUrl.protocol;
          url.host = apiUrl.host;
          url.port = apiUrl.port;
          return new Request(url.toString(), request);
        },
      });
    }

    // Configure authentication
    configureApiAuth(accessToken);
  }, [accessToken, api_url]);

  return <>{children}</>;
}
