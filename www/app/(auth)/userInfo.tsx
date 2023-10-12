"use client";
import {
  useFiefIsAuthenticated,
  useFiefUserinfo,
} from "@fief/fief/nextjs/react";
import Link from "next/link";

export default function UserInfo() {
  const isAuthenticated = useFiefIsAuthenticated();
  const userinfo = useFiefUserinfo();

  return !isAuthenticated ? (
    <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2">
      <Link href="/login" className="outline-none">
        Log in or create account
      </Link>
    </span>
  ) : (
    <span className="font-light px-2">
      {userinfo?.email} (
      <span className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px]">
        <Link href="/logout" className="outline-none">
          Log out
        </Link>
      </span>
      )
    </span>
  );
}
