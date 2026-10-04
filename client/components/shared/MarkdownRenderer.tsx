"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { MathJax } from "better-react-mathjax";
import { Box } from "@mui/material";

interface Props {
  content: string;
  /** Typeset LaTeX. Turn off while streaming — re-typesetting every token is expensive. */
  math?: boolean;
}

/** Markdown + LaTeX. Requires the MathJaxContext from app/providers.tsx. */
export default function MarkdownRenderer({ content, math = true }: Props) {
  const markdown = (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
      {content}
    </ReactMarkdown>
  );
  return (
    <Box
      sx={{
        "& h1,h2,h3,h4": { fontWeight: 600, mt: 2, mb: 1 },
        "& p": { mb: 1.5, lineHeight: 1.7 },
        "& code": { fontFamily: "monospace", bgcolor: "#f3f4f6", px: 0.5, borderRadius: 1 },
        "& pre": { bgcolor: "#f3f4f6", p: 2, borderRadius: 1, overflowX: "auto" },
        "& ul,ol": { pl: 3 },
      }}
    >
      {math ? <MathJax dynamic>{markdown}</MathJax> : markdown}
    </Box>
  );
}
