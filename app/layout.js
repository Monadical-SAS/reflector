import "./globals.scss";
import { Roboto } from "next/font/google";

import Head from "next/head";

const roboto = Roboto({ subsets: ["latin"], weight: "400" });

export const metadata = {
  title: "Reflector – Monadical",
  description: "Capture The Signal, Not The Noise",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <Head>
        <title>Test</title>
      </Head>
      <body className={roboto.className + " flex flex-col min-h-screen"}>
        <main className="flex-grow">
          {children}
        </main>
        <footer className="w-full bg-gray-800 text-white text-center py-4 fixed inset-x-0 bottom-0">
          © 2023 Reflector, a product of Monadical
        </footer>
        </body>

    </html>
  );
}
