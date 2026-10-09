import type { Metadata } from "next";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "katex/dist/katex.min.css";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "LearnAI",
  description: "AI-powered personalized learning platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
