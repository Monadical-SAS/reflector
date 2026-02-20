"use client";

import { Spinner, Link } from "@chakra-ui/react";
import { useAuth } from "../lib/AuthProvider";
import { usePathname } from "next/navigation";
import { getLogoutRedirectUrl } from "../lib/auth";

export default function UserInfo() {
  const auth = useAuth();
  const pathname = usePathname();
  const status = auth.status;
  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";
  const isRefreshing = status === "refreshing";

  const callbackUrl = getLogoutRedirectUrl(pathname);

  return isLoading ? (
    <Spinner size="xs" className="mx-3" />
  ) : !isAuthenticated && !isRefreshing ? (
    <Link
      href="#"
      className="font-light px-2"
      onClick={(e) => {
        e.preventDefault();
        auth.signIn();
      }}
    >
      Log in
    </Link>
  ) : (
    <Link
      href="#"
      className="font-light px-2"
      onClick={() => auth.signOut({ callbackUrl })}
    >
      Log out
    </Link>
  );
}
