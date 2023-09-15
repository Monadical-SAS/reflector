"use client";
import {
  useFiefIsAuthenticated,
  useFiefUserinfo,
} from "@fief/fief/nextjs/react";
import Link from "next/link";
import Image from "next/image";

export default function UserInfo() {
  const isAuthenticated = useFiefIsAuthenticated();
  const userinfo = useFiefUserinfo();

  return !isAuthenticated ? (
    <span className="hover:underline font-thin px-2">
      <Link href="/login">Log in or create account</Link>
    </span>
  ) : (
    <span className="font-thin px-2">
      {userinfo?.email} (
      <span className="hover:underline">
        <Link href="/logout">Log out</Link>
      </span>
      )
    </span>
  );
}
