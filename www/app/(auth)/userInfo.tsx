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

  return (
    <header className="bg-black w-full border-b border-gray-700 flex justify-between items-center py-2 mb-3">
      {/* Logo on the left */}
      <Link href="/">
        <Image
          src="/reach.png"
          width={16}
          height={16}
          className="h-6 w-auto ml-2"
          alt="Reflector"
        />
      </Link>

      {/* Text link on the right */}
      {!isAuthenticated && (
        <span className="text-white hover:underline font-thin px-2">
          <Link href="/login">Log in or create account</Link>
        </span>
      )}
      {isAuthenticated && (
        <span className="text-white font-thin px-2">
          {userinfo?.email} (
          <span className="hover:underline">
            <Link href="/logout">Log out</Link>
          </span>
          )
        </span>
      )}
    </header>
  );
}
