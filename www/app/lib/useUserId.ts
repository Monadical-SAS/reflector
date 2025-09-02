"use client";

import { useState, useEffect } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { Session } from "next-auth";
import { useAuth } from "./AuthProvider";

const assertUserId = <T>(u: T): T & { id: string } => {
  if (typeof (u as { id: string }).id !== "string")
    throw new Error("Expected user.id to be a string");
  return u as T & { id: string };
};

// the current assumption in useSessionUser is that "useNextAuthSession" also returns user.id, although useNextAuthSession documentation states it doesn't
// the hook is to isolate the potential impact and to document this behaviour
export default function useUserId() {
  const auth = useAuth();
  return auth.status === "authenticated" ? assertUserId(auth.user) : null;
}
