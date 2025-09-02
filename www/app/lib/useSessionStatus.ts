"use client";

import { useSession as useNextAuthSession } from "next-auth/react";

export default function useSessionStatus() {
  const { status } = useNextAuthSession();
  return status;
}
