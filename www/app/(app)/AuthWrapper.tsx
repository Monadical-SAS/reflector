"use client";

import { Flex, Spinner } from "@chakra-ui/react";
import useAuthReady from "../lib/useAuthReady";

export default function AuthWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthReady, isLoading } = useAuthReady();

  // Show spinner while auth is loading
  if (isLoading || !isAuthReady) {
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="calc(100vh - 80px)" // Account for header height
      >
        <Spinner size="xl" color="blue.500" thickness="4px" />
      </Flex>
    );
  }

  return <>{children}</>;
}
