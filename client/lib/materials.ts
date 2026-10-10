import type { CollectionMaterials, MaterialKind } from "@/types/collection";

/** A single material, in the shape a collection stores it. */
export type MaterialRef = CollectionMaterials[MaterialKind][number];

export const KIND_LABELS: Record<MaterialKind, { one: string; many: string }> = {
  textbook_sections: { one: "Book section", many: "Book sections" },
  transcriptions: { one: "Transcript", many: "Lectures & videos" },
  presentations: { one: "Slides", many: "Slides" },
  notes: { one: "Notes", many: "Notes" },
};

/** Stable identity of a material within its kind. */
export function materialId(kind: MaterialKind, ref: MaterialRef): string {
  const r = ref as unknown as Record<string, string | undefined>;
  switch (kind) {
    case "textbook_sections":
      return `${r.file_id}/${r.section_id}`;
    case "transcriptions":
      return r.transcription_id ?? r.job_id ?? "";
    case "presentations":
      return r.presentation_id ?? "";
    case "notes":
      return r.notes_id ?? "";
  }
}

/** Where a material can be viewed on its own. */
export function materialHref(kind: MaterialKind, ref: MaterialRef): string {
  const r = ref as unknown as Record<string, string | undefined>;
  switch (kind) {
    case "textbook_sections":
      return `/study/${r.file_id}/${encodeURIComponent(r.section_id ?? "")}`;
    case "transcriptions":
      return `/media/transcriptions/${materialId(kind, ref)}`;
    case "presentations":
      return `/media/presentations/${r.presentation_id}`;
    case "notes":
      return `/media/notes/${r.notes_id}`;
  }
}

export function hasMaterial(materials: CollectionMaterials, kind: MaterialKind, ref: MaterialRef): boolean {
  const id = materialId(kind, ref);
  return (materials[kind] as MaterialRef[]).some((m) => materialId(kind, m) === id);
}

export function withMaterial(materials: CollectionMaterials, kind: MaterialKind, ref: MaterialRef): CollectionMaterials {
  if (hasMaterial(materials, kind, ref)) return materials;
  return { ...materials, [kind]: [...materials[kind], ref] };
}

export function withoutMaterial(materials: CollectionMaterials, kind: MaterialKind, ref: MaterialRef): CollectionMaterials {
  const id = materialId(kind, ref);
  return { ...materials, [kind]: (materials[kind] as MaterialRef[]).filter((m) => materialId(kind, m) !== id) };
}

export const formatDate = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { dateStyle: "medium" });
};
