"use client";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ErrorAlert, LoadingState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";

// Served from public/vendor (copied from react-pdf's pdfjs-dist on install) — no CDN.
pdfjs.GlobalWorkerOptions.workerSrc = "/vendor/pdf.worker.min.mjs";

interface Props {
  url: string;
  /** Page number in the original book of this PDF's first page, for display */
  firstPage?: number;
}

/** Client-only: import with next/dynamic and { ssr: false }. Fits the page to the panel width. */
export default function PDFViewer({ url, firstPage = 1 }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [width, setWidth] = useState(440);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (error) {
    return (
      <div className="p-4">
        <ErrorAlert title="Failed to load PDF">{error}</ErrorAlert>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <div ref={boxRef} className="overflow-hidden rounded-lg border bg-white shadow-xs">
        <Document
          file={url}
          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          onLoadError={(e) => setError(e.message)}
          loading={<LoadingState label="Loading PDF…" />}
        >
          <Page pageNumber={page} width={width} />
        </Document>
      </div>

      {numPages > 0 && (
        <div className="sticky bottom-0 flex items-center justify-between gap-2 rounded-full border bg-background/90 p-1 shadow-sm backdrop-blur">
          <Button size="icon-sm" variant="ghost" className="rounded-full" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page">
            <ChevronLeftIcon />
          </Button>
          <span className="text-xs text-muted-foreground tabular-nums">
            Page {firstPage + page - 1} · {page} of {numPages}
          </span>
          <Button size="icon-sm" variant="ghost" className="rounded-full" disabled={page >= numPages} onClick={() => setPage((p) => p + 1)} aria-label="Next page">
            <ChevronRightIcon />
          </Button>
        </div>
      )}
    </div>
  );
}
