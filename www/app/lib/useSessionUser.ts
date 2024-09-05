"use client";

import { useState, useEffect } from "react";
import { useSession as useNextAuthSession } from "next-auth/react";
import { Session } from "next-auth";

// user type with id, name, email
export interface User {
  id?: string | null;
  name?: string | null;
  email?: string | null;
}

export default function useSessionUser() {
  const { data: session } = useNextAuthSession();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!session?.user) {
      setUser(null);
      return;
    }
    if (JSON.stringify(session.user) !== JSON.stringify(user)) {
      setUser(session.user);
    }
  }, [session]);

  return {
    id: user?.id,
    name: user?.name,
    email: user?.email,
  };
}
