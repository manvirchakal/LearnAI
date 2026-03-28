export interface Section {
  title: string;
  page: number;
}

export interface Chapter {
  number: string;
  title: string;
  page: number;
  sections: Section[];
}

export interface TextbookMetadata {
  title: string;
  s3_key: string;
  local_key?: string;
  user_id: string;
  document_type: string;
  table_of_contents: Chapter[];
}

export interface BookItem {
  title: string;
  s3_key: string;
  file_id?: string;
  author?: string;
  num_pages?: number;
}

export interface ChapterNode {
  id: string;
  title: string;
  sections: SectionNode[];
}

export interface SectionNode {
  id: string;
  title: string;
}

export interface BookStructure {
  chapters: ChapterNode[];
}
