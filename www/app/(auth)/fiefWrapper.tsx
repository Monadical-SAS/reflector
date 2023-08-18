"use client";

import { FiefAuthProvider } from "@fief/fief/nextjs/react";

export default function FiefWrapper({ children }) {
  return (
    <FiefAuthProvider currentUserPath="/api/current-user">
      {children}
    </FiefAuthProvider>
  );
}
