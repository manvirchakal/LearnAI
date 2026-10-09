"use client";
import { FileImageIcon, PaperclipIcon, UploadIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useUploadNotes } from "@/api/media";
import SuccessAlert from "./ResultAlert";

export default function NotesUpload() {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate: upload, data, isPending, isSuccess, error, reset } = useUploadNotes();

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">PDF or image (PNG, JPG) of handwritten or typed notes.</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Button
          variant="outline"
          className="min-w-0 justify-start sm:max-w-sm"
          onClick={() => inputRef.current?.click()}
          disabled={isPending}
        >
          {file ? <FileImageIcon className="text-primary" /> : <PaperclipIcon />}
          <span className="truncate">{file ? file.name : "Choose file"}</span>
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); reset(); } }}
        />
        {file && (
          <Button
            disabled={isPending}
            onClick={() =>
              upload(file, {
                onSuccess: () => {
                  setFile(null);
                  toast.success("Notes saved");
                },
              })
            }
          >
            {isPending ? <Spinner /> : <UploadIcon />}
            Upload
          </Button>
        )}
      </div>

      {isSuccess && (
        <SuccessAlert href={`/media/notes/${data.notes_id}`} linkLabel="View notes">
          Notes saved.
        </SuccessAlert>
      )}
      {error && <ErrorAlert title="Upload failed">{errorMessage(error)}</ErrorAlert>}
    </div>
  );
}
