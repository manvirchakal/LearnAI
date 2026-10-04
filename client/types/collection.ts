export interface TextbookSectionRef {
  file_id: string;
  section_id: string;
  title?: string;
}

export interface TranscriptionRef {
  /** Per-upload collections store transcription_id; job_id is accepted too */
  transcription_id?: string;
  job_id?: string;
  title?: string;
}

export interface PresentationRef {
  presentation_id: string;
  title?: string;
}

export interface NotesRef {
  notes_id: string;
  title?: string;
}

export interface CollectionMaterials {
  textbook_sections: TextbookSectionRef[];
  transcriptions: TranscriptionRef[];
  presentations: PresentationRef[];
  notes: NotesRef[];
  subcollections?: string[];
}

export interface Collection {
  collection_id: string;
  name: string;
  created_date: string;
  user_id: string;
  /** Created automatically for a single upload; hidden from the collections list */
  auto?: boolean;
  materials: CollectionMaterials;
}

export const MATERIAL_KINDS = ["textbook_sections", "transcriptions", "presentations", "notes"] as const;
export type MaterialKind = (typeof MATERIAL_KINDS)[number];

export const emptyMaterials = (): CollectionMaterials => ({
  textbook_sections: [],
  transcriptions: [],
  presentations: [],
  notes: [],
});

export const materialCount = (m: CollectionMaterials) =>
  MATERIAL_KINDS.reduce((n, kind) => n + (m[kind]?.length ?? 0), 0);
