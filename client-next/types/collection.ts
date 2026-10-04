export interface TextbookSectionRef {
  file_id: string;
  section_id: string;
  title?: string;
}

export interface CollectionMaterials {
  textbook_sections: TextbookSectionRef[];
  transcriptions: Record<string, unknown>[];
  presentations: Record<string, unknown>[];
  notes: Record<string, unknown>[];
  subcollections?: string[];
}

export interface Collection {
  collection_id: string;
  name: string;
  created_date: string;
  user_id: string;
  materials: CollectionMaterials;
}
