"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { MathJax, MathJaxContext } from "better-react-mathjax";
import { Box } from "@mui/material";

const mathJaxConfig = {
  loader: { load: ["input/tex", "output/chtml"] },
  tex: { inlineMath: [["$", "$"], ["\\(", "\\)"]], displayMath: [["$$", "$$"], ["\\[", "\\]"]] },
};

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <MathJaxContext config={mathJaxConfig}>
      <Box
        sx={{
          "& h1,h2,h3,h4": { fontWeight: 600, mt: 2, mb: 1 },
          "& p": { mb: 1.5, lineHeight: 1.7 },
          "& code": { fontFamily: "monospace", bgcolor: "#f3f4f6", px: 0.5, borderRadius: 1 },
          "& pre": { bgcolor: "#f3f4f6", p: 2, borderRadius: 1, overflowX: "auto" },
          "& ul,ol": { pl: 3 },
        }}
      >
        <MathJax>
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {content}
          </ReactMarkdown>
        </MathJax>
      </Box>
    </MathJaxContext>
  );
}
