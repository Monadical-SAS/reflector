import { useAuth } from "./AuthProvider";

export const useUserName = (): string | null | undefined => {
  const auth = useAuth();
  if (auth.status !== "authenticated") return undefined;
  return auth.user?.name || null;
};
