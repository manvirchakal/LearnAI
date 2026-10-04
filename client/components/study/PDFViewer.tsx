"use client";
import { Alert, Box, Typography } from "@mui/material";
import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";

// Served from public/vendor (copied from react-pdf's pdfjs-dist on install) — no CDN.
pdfjs.GlobalWorkerOptions.workerSrc = "/vendor/pdf.worker.min.mjs";

interface Props {
  url: string;
  /** Page number in the original book of this PDF's first page, for display */
  firstPage?: number;
  width?: number;
}

/** Client-only: import with next/dynamic and { ssr: false }. */
export default function PDFViewer({ url, firstPage = 1, width = 440 }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  if (error) return <Alert severity="error" sx={{ m: 2 }}>Failed to load PDF: {error}</Alert>;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", p: 2 }}>
      <Document
        file={url}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
        onLoadError={(e) => setError(e.message)}
        loading={<Spinner label="Loading PDF…" />}
      >
        <Page pageNumber={page} width={width} />
      </Document>

      {numPages > 0 && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mt: 2 }}>
          <Button size="small" variant="outlined" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Typography variant="body2" color="text.secondary">
            Page {firstPage + page - 1} ({page} of {numPages})
          </Typography>
          <Button size="small" variant="outlined" disabled={page >= numPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </Box>
      )}
    </Box>
  );
}
