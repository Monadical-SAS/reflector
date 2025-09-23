import "./styles/globals.scss";
import { Metadata, Viewport } from "next";
import { Poppins } from "next/font/google";
import { ErrorProvider } from "./(errors)/errorContext";
import ErrorMessage from "./(errors)/errorMessage";
import { ErrorBoundary } from "@sentry/nextjs";
import { Providers } from "./providers";
import { assertExistsAndNonEmptyString } from "./lib/utils";
import { getClientEnv } from "./lib/clientEnv";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["200", "400", "600"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "black",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

const SITE_URL = assertExistsAndNonEmptyString(
  process.env.SITE_URL,
  "SITE_URL required",
);

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
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

const env = getClientEnv();

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={poppins.className} suppressHydrationWarning>
      <body
        className={"h-[100svh] w-[100svw] overflow-x-hidden relative"}
        data-env={JSON.stringify(env)}
      >
        <ErrorBoundary fallback={<p>"something went really wrong"</p>}>
          <ErrorProvider>
            <ErrorMessage />
            <Providers>{children}</Providers>
          </ErrorProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
