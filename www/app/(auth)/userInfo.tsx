"use client";

import { Spinner, Link } from "@chakra-ui/react";
import { useAuth } from "../lib/AuthProvider";

export default function UserInfo() {
  const auth = useAuth();
  const status = auth.status;
  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";
  const isRefreshing = status === "refreshing";
  return isLoading ? (
    <Spinner size="xs" className="mx-3" />
  ) : !isAuthenticated && !isRefreshing ? (
    <Link
      href="#"
      className="font-light px-2"
      onClick={(e) => {
        e.preventDefault();
        auth.signIn("authentik");
      }}
    >
      Log in
    </Link>
  ) : (
    <Link
      href="#"
      className="font-light px-2"
      onClick={() => auth.signOut({ callbackUrl: "/" })}
    >
      Log out
    </Link>
  );
}
