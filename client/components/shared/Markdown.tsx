"use client";
import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";
import { useTheme } from "next-themes";
import { memo, useMemo } from "react";
import { Streamdown, type MermaidOptions } from "streamdown";
import { cn } from "@/lib/utils";

/** Inline $…$ too: models write it far more often than \(…\). */
const math = createMathPlugin({ singleDollarTextMath: true });
export const markdownPlugins = { cjk, code, math, mermaid };

/**
 * Mermaid draws with fixed colors, so diagrams get a theme matching the page.
 * Use `mermaidKey` as the Streamdown key: rendered diagrams are SVG and only
 * pick up a new theme when they render again.
 */
export function useMermaidTheme(): { mermaid: MermaidOptions; mermaidKey: string } {
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return useMemo(
    () => ({
      mermaid: { config: { theme: dark ? "dark" : "neutral", fontFamily: "Geist Variable, ui-sans-serif, sans-serif" } },
      mermaidKey: dark ? "dark" : "light",
    }),
    [dark],
  );
}

/** remark-math only knows dollar delimiters; models also write \(…\) and \[…\]. */
export function normalizeMath(text: string): string {
  return text
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => `\n$$\n${m.trim()}\n$$\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => `$${m.trim()}$`);
}

interface Props {
  children: string;
  className?: string;
  /** Still being written: lets Streamdown finish unterminated markdown gracefully */
  streaming?: boolean;
}

/**
 * Markdown with GFM, KaTeX math, syntax-highlighted code and Mermaid diagrams
 * (Streamdown, the renderer AI Elements uses), built for streamed text.
 */
const Markdown = memo(function Markdown({ children, className, streaming = false }: Props) {
  const { mermaid, mermaidKey } = useMermaidTheme();
  return (
    <Streamdown
      key={mermaidKey}
      mermaid={mermaid}
      className={cn("size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0", className)}
      plugins={markdownPlugins}
      isAnimating={streaming}
    >
      {normalizeMath(children)}
    </Streamdown>
  );
});

export default Markdown;
