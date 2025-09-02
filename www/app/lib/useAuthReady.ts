"use client";

import { useAuth } from "./AuthProvider";

// TODO
export default function useAuthReady() {
  const auth = useAuth();

  return {
    isAuthenticated: auth.status === "authenticated",
    isLoading: auth.status === "loading",
  };
}
