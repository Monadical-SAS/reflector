import "../styles/globals.scss";
import { Poppins } from "next/font/google";
import { Metadata, Viewport } from "next";
import FiefWrapper from "../(auth)/fiefWrapper";
import UserInfo from "../(auth)/userInfo";
import { ErrorProvider } from "../(errors)/errorContext";
import ErrorMessage from "../(errors)/errorMessage";
import Image from "next/image";
import About from "../(aboutAndPrivacy)/about";
import Privacy from "../(aboutAndPrivacy)/privacy";
import { DomainContextProvider } from "./domainContext";
import { getConfig } from "../lib/edgeConfig";
import { ErrorBoundary } from "@sentry/nextjs";
import { cookies } from "next/dist/client/components/headers";
import { SESSION_COOKIE_NAME } from "../lib/fief";
import { Providers } from "../providers";
import NextLink from "next/link";
import { Container, Flex, Link } from "@chakra-ui/react";

const poppins = Poppins({ subsets: ["latin"], weight: ["200", "400", "600"] });

export const viewport: Viewport = {
  themeColor: "black",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.DEV_URL || "https://reflector.media"),
  title: {
    template: "%s – Reflector",
    default: "Reflector - AI-Powered Meeting Transcriptions by Monadical",
  },
  description:
    "Reflector is an AI-powered tool that transcribes your meetings with unparalleled accuracy, divides content by topics, and provides insightful summaries. Maximize your productivity with Reflector, brought to you by Monadical. Capture the signal, not the noise",
  applicationName: "Reflector",
  referrer: "origin-when-cross-origin",
  keywords: ["Reflector", "Monadical", "AI", "Meetings", "Transcription"],
  authors: [{ name: "Monadical Team", url: "https://monadical.com/team.html" }],
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },

  openGraph: {
    title: "Reflector",
    description:
      "Reflector is an AI-powered tool that transcribes your meetings with unparalleled accuracy, divides content by topics, and provides insightful summaries. Maximize your productivity with Reflector, brought to you by Monadical. Capture the signal, not the noise.",
    type: "website",
  },

  twitter: {
    card: "summary_large_image",
    title: "Reflector",
    description:
      "Reflector is an AI-powered tool that transcribes your meetings with unparalleled accuracy, divides content by topics, and provides insightful summaries. Maximize your productivity with Reflector, brought to you by Monadical. Capture the signal, not the noise.",
    images: ["/r-icon.png"],
  },

  icons: {
    icon: "/r-icon.png",
    shortcut: "/r-icon.png",
    apple: "/r-icon.png",
  },
  robots: { index: false, follow: false, noarchive: true, noimageindex: true },
};

type LayoutProps = {
  params: {
    domain: string;
  };
  children: any;
};

export default async function RootLayout({ children, params }: LayoutProps) {
  const config = await getConfig(params.domain);
  const { requireLogin, privacy, browse, rooms } = config.features;
  const hasAuthCookie = !!cookies().get(SESSION_COOKIE_NAME);

  return (
    <html lang="en">
      <body
        className={
          poppins.className + "h-[100svh] w-[100svw] overflow-hidden relative"
        }
      >
        <FiefWrapper hasAuthCookie={hasAuthCookie}>
          <DomainContextProvider config={config}>
            <ErrorBoundary fallback={<p>"something went really wrong"</p>}>
              <ErrorProvider>
                <ErrorMessage />
                <Providers>
                  <Container
                    minW="100vw"
                    maxH="100vh"
                    minH="100vh"
                    maxW="container.xl"
                    display="grid"
                    gridTemplateRows="auto minmax(0,1fr)"
                  >
                    <Flex
                      as="header"
                      justify="space-between"
                      alignItems="center"
                      w="100%"
                      py="2"
                      px="0"
                    >
                      {/* Logo on the left */}
                      <Link
                        as={NextLink}
                        href="/"
                        className="flex outline-blue-300 md:outline-none focus-visible:underline  underline-offset-2 decoration-[.5px] decoration-gray-500"
                      >
                        <Image
                          src="/reach.png"
                          width={16}
                          height={16}
                          className="h-10 w-auto"
                          alt="Reflector"
                        />
                        <div className="hidden flex-col ml-2 md:block">
                          <h1 className="text-[38px] font-bold tracking-wide leading-tight">
                            Reflector
                          </h1>
                          <p className="text-gray-500 text-xs tracking-tighter">
                            Capture the signal, not the noise
                          </p>
                        </div>
                      </Link>
                      <div>
                        {/* Text link on the right */}
                        <Link
                          as={NextLink}
                          href="/transcripts/new"
                          className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                        >
                          Create
                        </Link>
                        {browse ? (
                          <>
                            &nbsp;·&nbsp;
                            <Link
                              href="/browse"
                              as={NextLink}
                              className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                              prefetch={false}
                            >
                              Browse
                            </Link>
                          </>
                        ) : (
                          <></>
                        )}
                        {rooms ? (
                          <>
                            &nbsp;·&nbsp;
                            <Link
                              href="/rooms"
                              as={NextLink}
                              className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                              prefetch={false}
                            >
                              Rooms
                            </Link>
                          </>
                        ) : (
                          <></>
                        )}
                        &nbsp;·&nbsp;
                        <About buttonText="About" />
                        {privacy ? (
                          <>
                            &nbsp;·&nbsp;
                            <Privacy buttonText="Privacy" />
                          </>
                        ) : (
                          <></>
                        )}
                        {requireLogin ? (
                          <>
                            &nbsp;·&nbsp;
                            <UserInfo />
                          </>
                        ) : (
                          <></>
                        )}
                      </div>
                    </Flex>

                    {children}
                  </Container>
                </Providers>
              </ErrorProvider>
            </ErrorBoundary>
          </DomainContextProvider>
        </FiefWrapper>
      </body>
    </html>
  );
}
