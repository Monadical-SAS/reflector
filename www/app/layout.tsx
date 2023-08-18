import "./styles/globals.scss";
import { Roboto } from "next/font/google";
import { Metadata } from "next";
import FiefWrapper from "./(auth)/fiefWrapper";
import UserInfo from "./(auth)/userInfo";

const roboto = Roboto({ subsets: ["latin"], weight: "400" });

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
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={roboto.className + " flex flex-col min-h-screen"}>
        <FiefWrapper>
          <div id="container">
            <div className="flex flex-col items-center h-[100svh] bg-gradient-to-r from-[#8ec5fc30] to-[#e0c3fc42]">
              <UserInfo />

              <div className="h-[13svh] flex flex-col justify-center items-center">
                <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
                <p className="text-gray-500">
                  Capture The Signal, Not The Noise
                </p>
              </div>
              {children}
            </div>
          </div>
        </FiefWrapper>
      </body>
    </html>
  );
}
