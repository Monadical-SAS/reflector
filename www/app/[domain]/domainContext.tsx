"use client";
import { createContext, useContext, useEffect, useState } from "react";

type DomainContextType = {
  features: {
    requireLogin: boolean;
    privacy: boolean;
    browse: boolean;
  };
  apiUrl: string | null;
};

export const DomainContext = createContext<DomainContextType>({
  features: {
    requireLogin: false,
    privacy: true,
    browse: false,
  },
  apiUrl: null,
});

export const DomainContextProvider = ({ config, children }) => {
  const [context, setContext] = useState<DomainContextType>();

  useEffect(() => {
    if (!config) return;
    setContext({
      features: {
        requireLogin: !!config["features"]["requireLogin"],
        privacy: !!config["features"]["privacy"],
        browse: !!config["features"]["browse"],
      },
      apiUrl: config["api_url"],
    });
  }, [config]);

  if (!context) return;

  return (
    <DomainContext.Provider value={context}>{children}</DomainContext.Provider>
  );
};

export const featureEnabled = (
  featureName: "requireLogin" | "privacy" | "browse",
) => {
  const context = useContext(DomainContext);
  return context.features[featureName] as boolean | undefined;
};
