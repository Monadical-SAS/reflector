import { useAuth } from "./AuthProvider";

export const useUserName = (): string | null | undefined => {
  const auth = useAuth();
  if (auth.status !== "authenticated" && auth.status !== "refreshing")
    return undefined;
  return auth.user?.name || null;
};
