"use client";
import { signOut, signIn } from "next-auth/react";
import useSessionStatus from "../lib/useSessionStatus";
import { Spinner, Link } from "@chakra-ui/react";

export default function UserInfo() {
  const status = useSessionStatus();
  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";
  return isLoading ? (
    <Spinner size="xs" className="mx-3" />
  ) : !isAuthenticated ? (
    <Link
      href="/"
      className="font-light px-2"
      onClick={() => signIn("authentik")}
    >
      Log in
    </Link>
  ) : (
    <Link
      href="#"
      className="font-light px-2"
      onClick={() => signOut({ callbackUrl: "/" })}
    >
      Log out
    </Link>
  );
}
