"use client";
import { useFiefIsAuthenticated } from "@fief/fief/nextjs/react";
import Link from "next/link";

export default function UserInfo() {
  const isAuthenticated = useFiefIsAuthenticated();

  return !isAuthenticated ? (
    <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2">
      <Link href="/login" className="outline-none" prefetch={false}>
        Log in
      </Link>
    </span>
  ) : (
    <span className="font-light px-2">
      <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px]">
        <Link href="/logout" className="outline-none" prefetch={false}>
          Log out
        </Link>
      </span>
    </span>
  );
}
