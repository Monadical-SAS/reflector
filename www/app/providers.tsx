"use client";

import { ChakraProvider } from "@chakra-ui/react";
import system from "./styles/theme";

import { WherebyProvider } from "@whereby.com/browser-sdk/react";
import { Toaster } from "./components/ui/toaster";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { ApiAuthProvider } from "./lib/ApiAuthProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <NuqsAdapter>
      <QueryClientProvider client={queryClient}>
        <ApiAuthProvider>
          <ChakraProvider value={system}>
            <WherebyProvider>
              {children}
              <Toaster />
            </WherebyProvider>
          </ChakraProvider>
        </ApiAuthProvider>
      </QueryClientProvider>
    </NuqsAdapter>
  );
}
