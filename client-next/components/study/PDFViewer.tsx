"use client";
import { Box, Typography, Alert } from "@mui/material";
import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import Spinner from "@/components/ui/Spinner";
import Button from "@/components/ui/Button";

pdfjs.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.js`;

interface Props {
  pdfUrl: string;
}

export default function PDFViewer({ pdfUrl }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [error, setError] = useState<string | null>(null);

  if (error) {
    return <Alert severity="error">Failed to load PDF: {error}</Alert>;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", p: 2 }}>
      <Document
        file={pdfUrl}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
        onLoadError={(e) => setError(e.message)}
        loading={<Spinner label="Loading PDF…" />}
      >
        <Page
          pageNumber={pageNumber}
          width={Math.min(typeof window !== "undefined" ? window.innerWidth - 80 : 800, 900)}
          renderAnnotationLayer
          renderTextLayer
        />
      </Document>

      {numPages > 0 && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mt: 2 }}>
          <Button size="small" variant="outlined" disabled={pageNumber <= 1} onClick={() => setPageNumber((p) => p - 1)}>
            Previous
          </Button>
          <Typography variant="body2" color="text.secondary">
            Page {pageNumber} of {numPages}
          </Typography>
          <Button size="small" variant="outlined" disabled={pageNumber >= numPages} onClick={() => setPageNumber((p) => p + 1)}>
            Next
          </Button>
        </Box>
      )}
    </Box>
  );
}
