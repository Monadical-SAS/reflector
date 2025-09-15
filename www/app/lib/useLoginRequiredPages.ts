// for paths that are not supposed to be public
import { PROTECTED_PAGES } from "./auth";
import { usePathname } from "next/navigation";
import { useAuth } from "./AuthProvider";
import { useEffect } from "react";

const HOME = "/" as const;

export const useLoginRequiredPages = () => {
  const pathname = usePathname();
  const isProtected = PROTECTED_PAGES.test(pathname);
  const auth = useAuth();
  const isNotLoggedIn = auth.status === "unauthenticated";
  // safety
  const isLastDestination = pathname === HOME;
  const shouldRedirect = isNotLoggedIn && isProtected && !isLastDestination;
  useEffect(() => {
    if (!shouldRedirect) return;
    // on the backend, the redirect goes straight to the auth provider, but we don't have it because it's hidden inside next-auth middleware
    // so we just "softly" lead the user to the main page
    // warning: if HOME redirects somewhere else, we won't be protected by isLastDestination
    window.location.href = HOME;
  }, [shouldRedirect]);
  // optionally save from blink, since window.location.href takes a bit of time
  return shouldRedirect ? HOME : null;
};
