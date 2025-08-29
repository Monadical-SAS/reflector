"use client";

import { useState, useEffect } from "react";
import useSessionStatus from "./useSessionStatus";
import { isAuthConfigured } from "./apiClient";

/**
 * Hook to check if authentication is fully ready.
 * This ensures both the session is authenticated AND the API client token is configured.
 * Prevents race conditions where React Query fires requests before the token is set.
 */
export default function useAuthReady() {
  const { status, isAuthenticated } = useSessionStatus();
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    // Check if both session is authenticated and token is configured
    const checkAuthReady = () => {
      const ready = isAuthenticated && isAuthConfigured();
      setAuthReady(ready);
    };

    // Check immediately
    checkAuthReady();

    // Also check periodically for a short time to catch async updates
    const interval = setInterval(checkAuthReady, 100);

    // Stop checking after 2 seconds (auth should be ready by then)
    const timeout = setTimeout(() => clearInterval(interval), 2000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [isAuthenticated]);

  return {
    isAuthReady: authReady,
    isLoading: status === "loading",
    isAuthenticated,
  };
}
