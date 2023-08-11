import "./globals.scss";
import { Roboto } from "next/font/google";

import Head from "next/head";

const roboto = Roboto({ subsets: ["latin"], weight: "400" });

export const metadata = {
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
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <Head>
        <title>Test</title>
      </Head>
      <body className={roboto.className + " flex flex-col min-h-screen"}>
        {children}
      </body>
    </html>
  );
}
