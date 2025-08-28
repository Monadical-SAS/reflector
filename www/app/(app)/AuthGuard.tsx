"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { signIn } from "next-auth/react";
import useSessionStatus from "../lib/useSessionStatus";
import { Flex, Spinner } from "@chakra-ui/react";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

// Routes that should be accessible without authentication
const PUBLIC_ROUTES = ["/transcripts/new"];

export default function AuthGuard({
  children,
  requireAuth = true,
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, status } = useSessionStatus();
  const router = useRouter();
  const pathname = usePathname();

  // Check if current route is public
  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    pathname.startsWith(route),
  );

  useEffect(() => {
    // Don't require auth for public routes
    if (isPublicRoute) return;

    // Only redirect if we're sure the user is not authenticated and auth is required
    if (!isLoading && requireAuth && status === "unauthenticated") {
      // Instead of redirecting to /login, trigger NextAuth signIn
      signIn("authentik");
    }
  }, [isLoading, requireAuth, status, isPublicRoute]);

  // For public routes, always show content
  if (isPublicRoute) {
    return <>{children}</>;
  }

  // Show loading spinner while checking authentication
  if (
    isLoading ||
    (requireAuth && !isAuthenticated && status !== "unauthenticated")
  ) {
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="100%"
      >
        <Spinner size="xl" />
      </Flex>
    );
  }

  // If authentication is not required or user is authenticated, show content
  if (!requireAuth || isAuthenticated) {
    return <>{children}</>;
  }

  // Don't render anything while redirecting
  return null;
}
