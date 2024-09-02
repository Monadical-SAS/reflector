"use client";
import { useSession, signOut, signIn } from "next-auth/react";
import { Spinner } from "@chakra-ui/react";
import Link from "next/link";

export default function UserInfo() {
  const { status } = useSession();
  const sessionReady = status !== "loading";
  const isAuthenticated = status === "authenticated";

  return !sessionReady ? (
    <Spinner size="xs" thickness="1px" className="mx-3" />
  ) : !isAuthenticated ? (
    <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2">
      <Link
        href="/"
        onClick={() => signIn("authentik")}
        className="outline-none"
        prefetch={false}
      >
        Log in
      </Link>
    </span>
  ) : (
    <span className="font-light px-2">
      <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px]">
        <Link
          href="#"
          onClick={() => signOut({ callbackUrl: "/" })}
          className="outline-none"
          prefetch={false}
        >
          Log out
        </Link>
      </span>
    </span>
  );
}
