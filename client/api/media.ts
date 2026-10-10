import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  NotesDetail,
  NotesMetadata,
  NotesResult,
  PresentationDetail,
  PresentationMetadata,
  PresentationResult,
  TranscriptionDetail,
  TranscriptionMetadata,
  TranscriptionResult,
  TranscriptionTask,
} from "@/types/media";

export const mediaKeys = {
  transcriptions: ["media", "transcriptions"] as const,
  transcription: (jobId: string) => ["media", "transcriptions", jobId] as const,
  task: (taskId: string) => ["media", "tasks", taskId] as const,
  presentations: ["media", "presentations"] as const,
  presentation: (id: string) => ["media", "presentations", id] as const,
  notes: ["media", "notes"] as const,
  note: (id: string) => ["media", "notes", id] as const,
};

// ── Transcriptions (YouTube + lectures) ──────────────────────────────────────

export const useTranscriptions = () =>
  useQuery<TranscriptionMetadata[]>({
    queryKey: mediaKeys.transcriptions,
    queryFn: () => apiClient.get("/media/transcriptions").then((r) => r.data),
  });

export const useTranscription = (jobId: string) =>
  useQuery<TranscriptionDetail>({
    queryKey: mediaKeys.transcription(jobId),
    queryFn: () => apiClient.get(`/media/transcriptions/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    staleTime: Infinity,
  });

/** Starts transcribing a video on the server; follow it with useTranscriptionTask. */
export const useTranscribeYouTube = () =>
  useMutation<TranscriptionTask, Error, string>({
    mutationFn: (video_url) => apiClient.post("/media/youtube", { video_url }).then((r) => r.data),
  });

const TASK_POLL_MS = 1000;

/** Polls a transcription task until it finishes, then refreshes the transcript list and calls onDone. */
export const useTranscriptionTask = (taskId: string | undefined, onDone?: (result: TranscriptionResult) => void) => {
  const qc = useQueryClient();
  return useQuery<TranscriptionTask>({
    queryKey: mediaKeys.task(taskId ?? ""),
    queryFn: async () => {
      const task: TranscriptionTask = (await apiClient.get(`/media/tasks/${taskId}`)).data;
      if (task.status === "done" && task.result) {
        qc.invalidateQueries({ queryKey: mediaKeys.transcriptions, exact: true });
        onDone?.(task.result);
      }
      return task;
    },
    enabled: !!taskId,
    refetchInterval: (q) =>
      q.state.error || q.state.data?.status === "done" || q.state.data?.status === "failed" ? false : TASK_POLL_MS,
    refetchIntervalInBackground: true,
    retry: 3, // ride out a blip; a 404 (expired, or the server restarted) ends it
    staleTime: Infinity,
  });
};

export const useTranscribeLecture = () => {
  const qc = useQueryClient();
  return useMutation<TranscriptionResult, Error, { audio: Blob; filename: string; title: string }>({
    mutationFn: ({ audio, filename, title }) => {
      const form = new FormData();
      form.append("audio", audio, filename);
      form.append("title", title);
      return apiClient.post("/media/lectures", form).then((r) => r.data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mediaKeys.transcriptions, exact: true }),
  });
};

// ── Presentations ────────────────────────────────────────────────────────────

export const usePresentations = () =>
  useQuery<PresentationMetadata[]>({
    queryKey: mediaKeys.presentations,
    queryFn: () => apiClient.get("/media/presentations").then((r) => r.data),
  });

export const usePresentation = (id: string) =>
  useQuery<PresentationDetail>({
    queryKey: mediaKeys.presentation(id),
    queryFn: () => apiClient.get(`/media/presentations/${id}`).then((r) => r.data),
    enabled: !!id,
    staleTime: Infinity,
  });

export const useProcessPresentation = () => {
  const qc = useQueryClient();
  return useMutation<PresentationResult, Error, File>({
    mutationFn: (file) => {
      const form = new FormData();
      form.append("presentation", file);
      return apiClient.post("/media/presentations", form).then((r) => r.data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mediaKeys.presentations, exact: true }),
  });
};

// ── Notes ────────────────────────────────────────────────────────────────────

export const useNotesList = () =>
  useQuery<NotesMetadata[]>({
    queryKey: mediaKeys.notes,
    queryFn: () => apiClient.get("/notes").then((r) => r.data),
  });

export const useNotes = (id: string) =>
  useQuery<NotesDetail>({
    queryKey: mediaKeys.note(id),
    queryFn: () => apiClient.get(`/notes/${id}`).then((r) => r.data),
    enabled: !!id,
    staleTime: Infinity,
  });

export const useUploadNotes = () => {
  const qc = useQueryClient();
  return useMutation<NotesResult, Error, File>({
    mutationFn: (file) => {
      const form = new FormData();
      form.append("notes", file);
      return apiClient.post("/notes", form).then((r) => r.data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mediaKeys.notes, exact: true }),
  });
};
