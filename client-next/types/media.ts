export interface TranscriptionMetadata {
  job_id: string;
  title: string;
  original_filename: string;
  transcription_date: string;
  source_type: "upload" | "youtube";
  video_url?: string | null;
  video_id?: string | null;
}

export interface TranscriptionResult {
  job_id: string;
  title: string;
  transcript: string;
  metadata: TranscriptionMetadata;
  collection_id: string;
}

export interface PresentationMetadata {
  presentation_id: string;
  original_filename: string;
  upload_date: string;
  total_slides: number;
  has_speaker_notes: boolean;
  slide_titles: string[];
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
