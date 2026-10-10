"use client";
import { CloudUploadIcon, FileTextIcon, UploadIcon, XIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { useUploadBook } from "@/api/books";
import { errorMessage } from "@/api/client";
import { cn } from "@/lib/utils";
import SuccessAlert from "./ResultAlert";

export default function FileUploadZone() {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [tocPages, setTocPages] = useState("");
  const router = useRouter();
  const { mutate: upload, isPending, error, isSuccess } = useUploadBook();
  const tocValid = tocPages === "" || /^\d+-\d+$/.test(tocPages);

  const handleFile = useCallback((f: File) => {
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) return;
    setFile(f);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const handleUpload = () => {
    if (!file || !tocValid) return;
    upload(
      { file, tocPages: tocPages || undefined },
      {
        onSuccess: (book) => {
          toast.success(`Uploaded “${book.title}”`);
          router.push(`/study/${book.file_id}`);
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <label
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        htmlFor="pdf-upload-input"
        className={cn(
          "group flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border bg-muted/30 hover:border-primary/50 hover:bg-primary/5",
          isPending && "pointer-events-none opacity-70",
        )}
      >
        <input
          id="pdf-upload-input"
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleChange}
        />

        {file ? (
          <>
            <span className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
              <FileTextIcon className="size-6" />
            </span>
            <div className="min-w-0 max-w-full">
              <p className="truncate font-medium">{file.name}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB · click to choose another file
              </p>
            </div>
          </>
        ) : (
          <>
            <span
              className={cn(
                "flex size-12 items-center justify-center rounded-xl bg-background text-muted-foreground shadow-xs ring-1 ring-border transition group-hover:text-primary",
                dragOver && "text-primary",
              )}
            >
              <CloudUploadIcon className="size-6" />
            </span>
            <div>
              <p className="font-medium">
                Drop your PDF here, or <span className="text-primary">click to browse</span>
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">PDF files only</p>
            </div>
          </>
        )}
      </label>

      {file && !isSuccess && (
        <div className="grid gap-2">
          <Label htmlFor="toc-pages">
            Table of contents pages <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="toc-pages"
            placeholder="e.g. 5-9"
            value={tocPages}
            onChange={(e) => setTocPages(e.target.value.trim())}
            aria-invalid={!tocValid}
            disabled={isPending}
          />
          <p className={cn("text-xs", tocValid ? "text-muted-foreground" : "text-destructive")}>
            {tocValid
              ? "Only needed if the PDF has no built-in outline; the printed TOC on these pages is read by Claude."
              : "Use a page range like 5-9"}
          </p>
        </div>
      )}

      {error && <ErrorAlert title="Upload failed">{errorMessage(error)}</ErrorAlert>}
      {isSuccess && <SuccessAlert>Upload complete! Opening your book…</SuccessAlert>}

      {file && !isSuccess && (
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" disabled={isPending} onClick={() => { setFile(null); setTocPages(""); }}>
            <XIcon />
            Clear
          </Button>
          <Button disabled={!tocValid || isPending} onClick={handleUpload}>
            {isPending ? <Spinner /> : <UploadIcon />}
            {isPending ? "Uploading & parsing…" : "Upload PDF"}
          </Button>
        </div>
      )}
    </div>
  );
}
