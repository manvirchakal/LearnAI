"use client";
import { Alert, Box, IconButton, List, ListItem, ListItemIcon, ListItemText, ListSubheader, Tooltip, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import EditNoteIcon from "@mui/icons-material/EditNote";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import OndemandVideoIcon from "@mui/icons-material/OndemandVideo";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import Link from "next/link";
import { ReactNode } from "react";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useUpdateCollectionMaterials } from "@/api/collections";
import { KIND_LABELS, materialHref, materialId, withoutMaterial, type MaterialRef } from "@/lib/materials";
import { MATERIAL_KINDS, type Collection, type MaterialKind } from "@/types/collection";

export const KIND_ICONS: Record<MaterialKind, ReactNode> = {
  textbook_sections: <MenuBookIcon fontSize="small" color="primary" />,
  transcriptions: <OndemandVideoIcon fontSize="small" color="error" />,
  presentations: <SlideshowIcon fontSize="small" color="warning" />,
  notes: <DescriptionOutlinedIcon fontSize="small" color="success" />,
};

function label(kind: MaterialKind, ref: MaterialRef): string {
  const r = ref as unknown as Record<string, string | undefined>;
  return r.title || (kind === "textbook_sections" ? `Section ${r.section_id}` : `${KIND_LABELS[kind].one} ${materialId(kind, ref).slice(0, 8)}`);
}

/** A collection's materials, grouped by kind, each removable. */
export default function MaterialList({ collection, onEdit }: { collection: Collection; onEdit: () => void }) {
  const update = useUpdateCollectionMaterials();

  const remove = (kind: MaterialKind, ref: MaterialRef) =>
    update.mutate({ collectionId: collection.collection_id, materials: withoutMaterial(collection.materials, kind, ref) });

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <Button size="small" variant="outlined" startIcon={<EditNoteIcon fontSize="small" />} onClick={onEdit}>
          Choose materials
        </Button>
      </Box>
      {update.error && <Alert severity="error" sx={{ mb: 1 }}>{errorMessage(update.error)}</Alert>}
      {MATERIAL_KINDS.every((k) => !collection.materials[k].length) && (
        <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>Nothing here yet.</Typography>
      )}
      {MATERIAL_KINDS.filter((k) => collection.materials[k].length).map((kind) => (
        <List key={kind} dense disablePadding
          subheader={<ListSubheader disableSticky sx={{ lineHeight: "32px", px: 1 }}>{KIND_LABELS[kind].many}</ListSubheader>}>
          {(collection.materials[kind] as MaterialRef[]).map((ref) => (
            <ListItem
              key={materialId(kind, ref)}
              sx={{ px: 1 }}
              secondaryAction={
                <Tooltip title="Remove from collection">
                  <span>
                    <IconButton edge="end" size="small" onClick={() => remove(kind, ref)} disabled={update.isPending}
                      aria-label={`Remove ${label(kind, ref)}`}>
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </span>
                </Tooltip>
              }
            >
              <ListItemIcon sx={{ minWidth: 32 }}>{KIND_ICONS[kind]}</ListItemIcon>
              <ListItemText
                primary={
                  <Link href={materialHref(kind, ref)} style={{ color: "inherit" }}>{label(kind, ref)}</Link>
                }
                primaryTypographyProps={{ variant: "body2", noWrap: true }}
              />
            </ListItem>
          ))}
        </List>
      ))}
    </Box>
  );
}
