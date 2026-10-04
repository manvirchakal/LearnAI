"use client";
import { Alert, Box, Grid, TextField, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FolderSpecialOutlinedIcon from "@mui/icons-material/FolderSpecialOutlined";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { KIND_ICONS } from "@/components/collections/MaterialList";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import { useCollections, useCreateCollection } from "@/api/collections";
import { formatDate, KIND_LABELS } from "@/lib/materials";
import { emptyMaterials, MATERIAL_KINDS, materialCount, type Collection } from "@/types/collection";

function CollectionCard({ collection }: { collection: Collection }) {
  const count = materialCount(collection.materials);
  return (
    <Link href={`/collections/${collection.collection_id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <Card sx={{
        height: "100%",
        transition: "transform 0.15s, box-shadow 0.15s",
        "&:hover": { transform: "translateY(-2px)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" },
      }}>
        <Typography fontWeight={600} variant="body2" noWrap title={collection.name}>{collection.name}</Typography>
        <Typography variant="caption" color="text.secondary">
          {count} {count === 1 ? "item" : "items"} · {formatDate(collection.created_date)}
        </Typography>
        <Box sx={{ display: "flex", gap: 1.5, mt: 1.5, flexWrap: "wrap" }}>
          {MATERIAL_KINDS.filter((k) => collection.materials[k].length).map((k) => (
            <Box key={k} title={KIND_LABELS[k].many} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {KIND_ICONS[k]}
              <Typography variant="caption">{collection.materials[k].length}</Typography>
            </Box>
          ))}
        </Box>
      </Card>
    </Link>
  );
}

export default function CollectionsPage() {
  const router = useRouter();
  const { data: collections = [], isPending, error } = useCollections();
  const create = useCreateCollection();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const submit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate({ name: trimmed, materials: emptyMaterials() }, {
      onSuccess: (col) => router.push(`/collections/${col.collection_id}`),
    });
  };

  return (
    <AppShell>
      <Box sx={{ p: 4 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 3 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" fontWeight={700} gutterBottom>Collections</Typography>
            <Typography variant="body2" color="text.secondary">
              Group book sections, lectures, slides and notes, then study and chat over them together.
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>New collection</Button>
        </Box>

        {isPending && <Spinner label="Loading collections…" />}
        {error && <Alert severity="error">Failed to load collections: {errorMessage(error)}</Alert>}
        {!isPending && !error && collections.length === 0 && (
          <Box sx={{ textAlign: "center", py: 8 }}>
            <FolderSpecialOutlinedIcon sx={{ fontSize: 48, color: "text.disabled", mb: 1 }} />
            <Typography color="text.secondary">
              No collections yet. Create one, or use &ldquo;Add to collection&rdquo; on any section or upload.
            </Typography>
          </Box>
        )}
        <Grid container spacing={2}>
          {collections.map((c) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={c.collection_id}>
              <CollectionCard collection={c} />
            </Grid>
          ))}
        </Grid>
      </Box>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New collection"
        maxWidth="xs"
        fullWidth
        actions={
          <>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="contained" onClick={submit} disabled={!name.trim()} loading={create.isPending}>Create</Button>
          </>
        }
      >
        <TextField autoFocus fullWidth size="small" label="Name" value={name} sx={{ mt: 1 }}
          onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} />
        {create.error && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(create.error)}</Alert>}
      </Modal>
    </AppShell>
  );
}
