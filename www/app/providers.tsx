"use client";

import { ChakraProvider } from "@chakra-ui/react";
import system from "./styles/theme";

import { WherebyProvider } from "@whereby.com/browser-sdk/react";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={system}>
      <WherebyProvider>{children}</WherebyProvider>
    </ChakraProvider>
  );
}
