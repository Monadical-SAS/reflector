import "./styles/globals.scss";
import { Poppins } from "next/font/google";
import { Metadata } from "next";
import FiefWrapper from "./(auth)/fiefWrapper";
import UserInfo from "./(auth)/userInfo";
import { ErrorProvider } from "./(errors)/errorContext";
import ErrorMessage from "./(errors)/errorMessage";
import Image from "next/image";
import Link from "next/link";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
});

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

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="overflow-x-hidden">
      <body className={poppins.className + " relative"}>
        <FiefWrapper>
          <ErrorProvider>
            <ErrorMessage />
            <div
              id="container"
              className="items-center min-h-[100svh] w-[100svw] p-2 md:p-4 grid grid-rows-layout gap-2 md:gap-4"
            >
              <header className="flex justify-between items-center w-full">
                {/* Logo on the left */}
                <Link
                  href="/"
                  className="flex outline-blue-300 md:outline-none focus-visible:underline  underline-offset-2 decoration-[.5px] decoration-gray-500"
                >
                  <Image
                    src="/reach.png"
                    width={40}
                    height={40}
                    className="h-10 w-auto"
                    alt="Reflector"
                  />
                </Link>
              </header>

              {children}
            </div>
          </ErrorProvider>
        </FiefWrapper>
      </body>
    </html>
  );
}
