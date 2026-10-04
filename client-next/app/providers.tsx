"use client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClientProvider } from "@tanstack/react-query";
import { MathJaxContext } from "better-react-mathjax";
import { ReactNode } from "react";
import theme from "@/lib/theme";
import { queryClient } from "@/lib/queryClient";
import { MATHJAX_SRC, mathJaxConfig } from "@/lib/mathjax";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MathJaxContext src={MATHJAX_SRC} config={mathJaxConfig}>
          {children}
        </MathJaxContext>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
