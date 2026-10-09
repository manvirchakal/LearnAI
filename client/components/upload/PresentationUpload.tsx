"use client";
import { PaperclipIcon, PresentationIcon, WandSparklesIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useProcessPresentation } from "@/api/media";
import SuccessAlert from "./ResultAlert";

export default function PresentationUpload() {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate: upload, data, isPending, isSuccess, error, reset } = useProcessPresentation();

  const handleFile = (f: File) => {
    if (!/\.pptx$/i.test(f.name)) return;
    setFile(f);
    reset();
  };

  const handleUpload = () => {
    if (!file) return;
    upload(file, {
      onSuccess: (res) => {
        setFile(null);
        toast.success(`${res.metadata.total_slides} slides saved`);
      },
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">PowerPoint decks (.pptx) are split into slides with extracted text.</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Button
          variant="outline"
          className="min-w-0 justify-start sm:max-w-sm"
          onClick={() => inputRef.current?.click()}
          disabled={isPending}
        >
          {file ? <PresentationIcon className="text-primary" /> : <PaperclipIcon />}
          <span className="truncate">{file ? file.name : "Choose .pptx file"}</span>
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".pptx"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {file && (
          <Button disabled={isPending} onClick={handleUpload}>
            {isPending ? <Spinner /> : <WandSparklesIcon />}
            Process
          </Button>
        )}
      </div>

      {isSuccess && (
        <SuccessAlert href={`/media/presentations/${data.presentation_id}`} linkLabel="View slides">
          {data.metadata.total_slides} slides saved.
        </SuccessAlert>
      )}
      {error && <ErrorAlert title="Failed to process presentation">{errorMessage(error)}</ErrorAlert>}
    </div>
  );
}
