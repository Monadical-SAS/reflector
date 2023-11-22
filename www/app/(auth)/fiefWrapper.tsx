"use client";

import { FiefAuthProvider } from "@fief/fief/nextjs/react";
import { createContext } from "react";

export const CookieContext = createContext<{ hasAuthCookie: boolean }>({
  hasAuthCookie: false,
});

export default function FiefWrapper({ children, hasAuthCookie }) {
  return (
    <CookieContext.Provider value={{ hasAuthCookie }}>
      <FiefAuthProvider currentUserPath="/api/current-user">
        {children}
      </FiefAuthProvider>
    </CookieContext.Provider>
  );
}
