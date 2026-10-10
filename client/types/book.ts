export interface Section {
  /** Stable, URL-safe id, e.g. "ch3.s2" */
  id: string;
  title: string;
  start_page: number;
  end_page: number;
}

export interface Chapter {
  id: string;
  number: string;
  title: string;
  start_page: number;
  end_page: number;
  sections: Section[];
}

export interface BookSummary {
  file_id: string;
  title: string;
  filename: string;
  document_type: string;
  num_pages: number;
  chapter_count: number;
  section_count: number;
  uploaded_at: string;
}

export interface BookDetail extends BookSummary {
  chapters: Chapter[];
}

export interface UploadBookInput {
  file: File;
  documentType?: "textbook" | "notes" | "other";
  /** Printed TOC page range for PDFs without an embedded outline, e.g. "5-9" */
  tocPages?: string;
}
