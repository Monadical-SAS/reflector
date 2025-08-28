"use client";

import { useEffect, useContext, useRef } from "react";
import { client, configureApiAuth } from "./apiClient";
import useSessionAccessToken from "./useSessionAccessToken";
import { DomainContext } from "../domainContext";

// Store the current API URL globally
let currentApiUrl: string | null = null;

// Set up base URL middleware once
const baseUrlMiddlewareSetup = () => {
  client.use({
    onRequest({ request }) {
      if (currentApiUrl) {
        // Update the base URL for all requests
        const url = new URL(request.url);
        const apiUrl = new URL(currentApiUrl);
        url.protocol = apiUrl.protocol;
        url.host = apiUrl.host;
        url.port = apiUrl.port;
        return new Request(url.toString(), request);
      }
      return request;
    },
  });
};

// Initialize base URL middleware once
if (typeof window !== "undefined") {
  baseUrlMiddlewareSetup();
}

export function ApiAuthProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useSessionAccessToken();
  const { api_url } = useContext(DomainContext);
  const initialized = useRef(false);

  // Initialize middleware once on client side
  useEffect(() => {
    if (!initialized.current && typeof window !== "undefined") {
      baseUrlMiddlewareSetup();
      initialized.current = true;
    }
  }, []);

  useEffect(() => {
    // Update the global API URL
    currentApiUrl = api_url;
  }, [api_url]);

  useEffect(() => {
    // Configure authentication
    configureApiAuth(accessToken);
  }, [accessToken]);

  return <>{children}</>;
}
