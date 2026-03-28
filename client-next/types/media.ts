export interface TranscriptionMetadata {
  job_id: string;
  title: string;
  original_filename: string;
  transcription_date: string;
  source_type: "upload" | "youtube";
  video_url?: string;
}

export interface TranscriptionResult {
  transcript: string;
  metadata: TranscriptionMetadata;
  job_id: string;
  collection_id: string;
  video_title?: string;
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
  metadata: PresentationMetadata;
  slides: SlideContent[];
}
