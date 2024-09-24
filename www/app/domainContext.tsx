"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { DomainConfig } from "./lib/edgeConfig";

type DomainContextType = Omit<DomainConfig, "auth_callback_url">;

export const DomainContext = createContext<DomainContextType>({
  features: {
    requireLogin: false,
    privacy: true,
    browse: false,
    sendToZulip: false,
  },
  api_url: "",
  websocket_url: "",
});

export const DomainContextProvider = ({
  config,
  children,
}: {
  config: DomainConfig;
  children: any;
}) => {
  const [context, setContext] = useState<DomainContextType>();

  useEffect(() => {
    if (!config) return;
    const { auth_callback_url, ...others } = config;
    setContext(others);
  }, [config]);

  if (!context) return;

  return (
    <DomainContext.Provider value={context}>{children}</DomainContext.Provider>
  );
};

// Get feature config client-side with
export const featureEnabled = (
  featureName: "requireLogin" | "privacy" | "browse" | "sendToZulip",
) => {
  const context = useContext(DomainContext);

  return context.features[featureName] as boolean | undefined;
};

// Get config server-side (out of react) : see lib/edgeConfig.
