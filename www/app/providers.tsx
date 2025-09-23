"use client";

import { ChakraProvider } from "@chakra-ui/react";
import system from "./styles/theme";
import dynamic from "next/dynamic";

import { Toaster } from "./components/ui/toaster";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { AuthProvider } from "./lib/AuthProvider";
import { SessionProvider as SessionProviderNextAuth } from "next-auth/react";

const WherebyProvider = dynamic(
  () =>
    import("@whereby.com/browser-sdk/react").then((mod) => ({
      default: mod.WherebyProvider,
    })),
  { ssr: false },
);

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <NuqsAdapter>
      <QueryClientProvider client={queryClient}>
        <SessionProviderNextAuth>
          <AuthProvider>
            <ChakraProvider value={system}>
              <WherebyProvider>
                {children}
                <Toaster />
              </WherebyProvider>
            </ChakraProvider>
          </AuthProvider>
        </SessionProviderNextAuth>
      </QueryClientProvider>
    </NuqsAdapter>
  );
}
