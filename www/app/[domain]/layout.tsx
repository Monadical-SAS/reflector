import "../styles/globals.scss";
import { Poppins } from "next/font/google";
import { Metadata } from "next";
import FiefWrapper from "../(auth)/fiefWrapper";
import UserInfo from "../(auth)/userInfo";
import { ErrorProvider } from "../(errors)/errorContext";
import ErrorMessage from "../(errors)/errorMessage";
import Image from "next/image";
import Link from "next/link";
import About from "../(aboutAndPrivacy)/about";
import Privacy from "../(aboutAndPrivacy)/privacy";
import { DomainContextProvider } from "./domainContext";
import { getConfig } from "../lib/edgeConfig";

const poppins = Poppins({ subsets: ["latin"], weight: ["200", "400", "600"] });

export const metadata: Metadata = {
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
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
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
  const { requireLogin, privacy, browse } = config.features;

  return (
    <html lang="en">
      <body className={poppins.className + " h-screen relative"}>
        <FiefWrapper>
          <DomainContextProvider config={config}>
            <ErrorProvider>
              <ErrorMessage />
              <div
                id="container"
                className="items-center h-[100svh] w-[100svw] p-2 md:p-4 grid grid-rows-layout gap-2 md:gap-4"
              >
                <header className="flex justify-between items-center w-full">
                  {/* Logo on the left */}
                  <Link
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
                          className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                        >
                          Browse
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
                </header>

                {children}
              </div>
            </ErrorProvider>
          </DomainContextProvider>
        </FiefWrapper>
      </body>
    </html>
  );
}
