export interface TranscriptionMetadata {
  job_id: string;
  title: string;
  original_filename: string;
  transcription_date: string;
  source_type: "upload" | "youtube";
  video_url?: string | null;
  video_id?: string | null;
  /** The collection created for this transcript alone (absent on older uploads) */
  collection_id?: string;
}

export interface TranscriptionResult {
  job_id: string;
  title: string;
  transcript: string;
  metadata: TranscriptionMetadata;
  collection_id: string;
}

/** A transcription running on the server, polled at GET /media/tasks/{task_id} */
export interface TranscriptionTask {
  task_id: string;
  status: "queued" | "running" | "done" | "failed";
  stage: "queued" | "downloading" | "transcribing" | "saving" | "indexing" | "done";
  /** Fraction of the current stage done, 0-1; null when unknown */
  progress: number | null;
  /** The video's title, once known */
  title: string | null;
  result: TranscriptionResult | null;
  error: string | null;
}

export interface TranscriptionDetail {
  metadata: TranscriptionMetadata;
  transcript: string;
}

export interface PresentationMetadata {
  presentation_id: string;
  original_filename: string;
  upload_date: string;
  total_slides: number;
  has_speaker_notes: boolean;
  slide_titles: string[];
  collection_id?: string;
}

export interface SlideContent {
  title: string;
  content: string[];
  notes: string;
}

export interface PresentationResult {
  presentation_id: string;
  collection_id: string;
  metadata: PresentationMetadata;
  slides: SlideContent[];
}

export interface PresentationDetail {
  metadata: PresentationMetadata;
  slides: SlideContent[];
}

export interface NotesMetadata {
  notes_id: string;
  original_filename: string;
  upload_date: string;
  file_type: string;
  processing_status: string;
  collection_id?: string;
}

export interface NotesTextBlock {
  text: string;
}

export interface NotesDetail {
  metadata: NotesMetadata;
  content: { text_content: NotesTextBlock[] };
}

export interface NotesResult {
  notes_id: string;
  metadata: NotesMetadata;
  collection_id: string;
}
