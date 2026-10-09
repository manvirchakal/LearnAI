"use client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { queryClient } from "@/lib/queryClient";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <TooltipProvider delayDuration={300}>
          {children}
          {/* On phones toasts sit above the bottom tab bar */}
          <Toaster richColors position="bottom-right" mobileOffset={{ bottom: "calc(var(--bottom-bar) + 0.5rem)" }} />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
