import "./styles/globals.scss";
import { Poppins } from "next/font/google";
import { Metadata } from "next";
import FiefWrapper from "./(auth)/fiefWrapper";
import UserInfo from "./(auth)/userInfo";
import { ErrorProvider } from "./(errors)/errorContext";
import ErrorMessage from "./(errors)/errorMessage";
import Image from "next/image";

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
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={poppins.className + " flex flex-col min-h-screen"}>
        <FiefWrapper>
          <ErrorProvider>
            <ErrorMessage />
            {/*TODO lvh or svh ? */}
            <div
              id="container"
              className="flex flex-col items-center min-h-[100svh]"
            >
              <header className="flex justify-between items-center p-2 md:p-4 w-full">
                {/* Logo on the left */}
                <div className="flex">
                  <Image
                    src="/reach.png"
                    width={16}
                    height={16}
                    className="h-10 w-auto mr-2"
                    alt="Reflector"
                  />
                  <div className="hidden flex-col md:flex">
                    <h1 className="text-4xl font-bold">Reflector</h1>
                    <p className="text-gray-500">
                      Capture The Signal, Not The Noise
                    </p>
                  </div>
                </div>
                {/* Text link on the right */}
                <UserInfo />
              </header>

              {children}
            </div>
          </ErrorProvider>
        </FiefWrapper>
      </body>
    </html>
  );
}
