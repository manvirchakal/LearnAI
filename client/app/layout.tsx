import type { Metadata } from "next";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "LearnAI",
  description: "AI-powered personalized learning platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body id="__next">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
