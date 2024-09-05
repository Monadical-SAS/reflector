"use client";

import { useState, useEffect } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { Session } from "next-auth";

export default function useSessionStatus() {
  const { status: naStatus } = useNextAuthSession();
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    if (naStatus !== "loading" && naStatus !== status) {
      setStatus(naStatus);
    }
  }, [naStatus]);

  return {
    status,
    isLoading: status === "loading",
    isAuthenticated: status === "authenticated",
  };
}
