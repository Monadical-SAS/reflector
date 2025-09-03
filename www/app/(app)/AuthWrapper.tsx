"use client";

import { Flex, Spinner } from "@chakra-ui/react";
import { useAuth } from "../lib/AuthProvider";

export default function AuthWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const auth = useAuth();

  if (auth.status === "loading") {
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="calc(100vh - 80px)" // Account for header height
      >
        <Spinner size="xl" color="blue.500" />
      </Flex>
    );
  }

  return <>{children}</>;
}
