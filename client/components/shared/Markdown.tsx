"use client";
import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";
import { memo } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";

/** Inline $…$ too: models write it far more often than \(…\). */
const math = createMathPlugin({ singleDollarTextMath: true });
export const markdownPlugins = { cjk, code, math, mermaid };

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
  return (
    <Streamdown
      className={cn("size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0", className)}
      plugins={markdownPlugins}
      isAnimating={streaming}
    >
      {normalizeMath(children)}
    </Streamdown>
  );
});

export default Markdown;
