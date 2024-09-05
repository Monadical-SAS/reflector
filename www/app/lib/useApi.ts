import { useSession, signOut } from "next-auth/react";
import { useContext, useEffect, useState } from "react";
import { DomainContext, featureEnabled } from "../domainContext";
import { OpenApi, DefaultService } from "../api";
import { CustomSession } from "./types";
import useSessionStatus from "./useSessionStatus";
import useSessionAccessToken from "./useSessionAccessToken";

export default function useApi(): DefaultService | null {
  const api_url = useContext(DomainContext).api_url;
  const [api, setApi] = useState<OpenApi | null>(null);
  const { isReady, isAuthenticated } = useSessionStatus();
  const { accessToken, error } = useSessionAccessToken();

  if (!api_url) throw new Error("no API URL");

  useEffect(() => {
    if (error === "RefreshAccessTokenError") {
      signOut();
    }
  }, [error]);

  useEffect(() => {
    if (!isReady || (isAuthenticated && !accessToken)) {
      return;
    }

    const openApi = new OpenApi({
      BASE: api_url,
      TOKEN: accessToken || undefined,
    });

    setApi(openApi);
  }, [isReady, isAuthenticated, accessToken]);

  return api?.default ?? null;
}
