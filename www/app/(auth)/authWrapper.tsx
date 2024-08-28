import { useSession, signIn } from "next-auth/react";
import { getServerSession } from "next-auth";
import SessionProvider from "../lib/SessionProvider";

export default async function AuthWrapper({ children }) {
  const session = await getServerSession();
  return <SessionProvider session={session}>{children}</SessionProvider>;
}
