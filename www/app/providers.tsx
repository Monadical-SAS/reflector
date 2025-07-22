"use client";

import { ChakraProvider } from "@chakra-ui/react";
import system from "./styles/theme";

import { WherebyProvider } from "@whereby.com/browser-sdk/react";
import { Toaster } from "./components/ui/toaster";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={system}>
      <WherebyProvider>
        {children}
        <Toaster />
      </WherebyProvider>
    </ChakraProvider>
  );
}
