"use client";
import { useEffect, useRef, useState } from "react";
import { Box, Typography } from "@mui/material";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

let diagramCounter = 0;

interface Props {
  diagram: string;
}

export default function MermaidDiagram({ diagram }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ref.current || !diagram) return;
    const id = `mermaid-${++diagramCounter}`;
    ref.current.innerHTML = "";

    let attempts = 0;
    const render = async () => {
      try {
        const { svg } = await mermaid.render(id, diagram);
        if (ref.current) ref.current.innerHTML = svg;
        setError(null);
      } catch (e) {
        attempts++;
        if (attempts < 3) setTimeout(render, 500);
        else setError(String(e));
      }
    };
    render();
  }, [diagram]);

  if (error) {
    return (
      <Typography variant="body2" color="error" sx={{ p: 1, fontFamily: "monospace", fontSize: 12 }}>
        Diagram render error: {error}
      </Typography>
    );
  }

  return <Box ref={ref} sx={{ overflowX: "auto" }} />;
}
