"use client";
import { Alert, Box, List, ListItemButton, ListItemIcon, ListItemText, TextField, Typography } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import { useState } from "react";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import { useCollections, useCreateCollection, useUpdateCollectionMaterials } from "@/api/collections";
import { hasMaterial, withMaterial, type MaterialRef } from "@/lib/materials";
import { emptyMaterials, materialCount, type Collection, type MaterialKind } from "@/types/collection";

interface Props {
  kind: MaterialKind;
  item: MaterialRef;
  size?: "small" | "medium";
}

/** Adds one material to an existing collection, or to a new one. */
export default function AddToCollectionButton({ kind, item, size = "small" }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const collections = useCollections();
  const update = useUpdateCollectionMaterials();
  const create = useCreateCollection();
  const error = update.error ?? create.error ?? collections.error;

  const add = (col: Collection) => {
    if (hasMaterial(col.materials, kind, item)) return;
    update.mutate({ collectionId: col.collection_id, materials: withMaterial(col.materials, kind, item) });
  };

  const createWithItem = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate(
      { name: trimmed, materials: withMaterial(emptyMaterials(), kind, item) },
      { onSuccess: () => setName("") },
    );
  };

  return (
    <>
      <Button size={size} variant="outlined" startIcon={<PlaylistAddIcon fontSize="small" />} onClick={() => setOpen(true)}>
        Add to collection
      </Button>
      <Modal open={open} onClose={() => setOpen(false)} title="Add to collection" maxWidth="xs" fullWidth>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage(error)}</Alert>}
        {collections.isPending ? (
          <Spinner size={24} />
        ) : collections.data?.length ? (
          <List dense disablePadding sx={{ mb: 2, maxHeight: 320, overflowY: "auto" }}>
            {collections.data.map((col) => {
              const added = hasMaterial(col.materials, kind, item);
              const busy = update.isPending && update.variables?.collectionId === col.collection_id;
              return (
                <ListItemButton key={col.collection_id} onClick={() => add(col)} disabled={busy || added}
                  sx={{ borderRadius: 1, "&.Mui-disabled": { opacity: added ? 1 : 0.5 } }}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {added ? <CheckIcon color="success" fontSize="small" /> : <FolderOutlinedIcon fontSize="small" />}
                  </ListItemIcon>
                  <ListItemText
                    primary={col.name}
                    secondary={added ? "Added" : `${materialCount(col.materials)} items`}
                  />
                </ListItemButton>
              );
            })}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            You don&apos;t have any collections yet.
          </Typography>
        )}
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="New collection name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createWithItem()}
            inputProps={{ "aria-label": "New collection name" }}
          />
          <Button variant="contained" onClick={createWithItem} disabled={!name.trim()} loading={create.isPending}>
            Create
          </Button>
        </Box>
      </Modal>
    </>
  );
}
