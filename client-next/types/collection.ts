export interface TextbookSectionRef {
  section_id: string;
  title: string;
  page: number;
  local_key: string;
  added_date: string;
}

export interface CollectionMaterials {
  textbook_sections: Record<string, unknown>[];
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
  chapter_number?: string;
  parent_chapter?: string;
  materials: CollectionMaterials;
}
