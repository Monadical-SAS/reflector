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
      <body className={roboto.className}>{children}</body>
    </html>
  );
}
