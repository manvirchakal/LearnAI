"use client";
import { Alert, Box, Divider, IconButton, TextField, Tooltip, Typography } from "@mui/material";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import CheckIcon from "@mui/icons-material/Check";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ForumIcon from "@mui/icons-material/Forum";
import ListAltIcon from "@mui/icons-material/ListAlt";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import { useRouter } from "next/navigation";
import { useState } from "react";
import MaterialList from "@/components/collections/MaterialList";
import MaterialPicker from "@/components/collections/MaterialPicker";
import AppShell from "@/components/layout/AppShell";
import ChatPanel from "@/components/study/ChatPanel";
import DiagramPanel from "@/components/study/DiagramPanel";
import GamePanel from "@/components/study/GamePanel";
import NarrativePanel from "@/components/study/NarrativePanel";
import { StudySessionProvider } from "@/components/study/StudySession";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import Tabs from "@/components/ui/Tabs";
import { errorMessage } from "@/api/client";
import { useCollection, useDeleteCollection, useRenameCollection } from "@/api/collections";
import { collectionUnit } from "@/api/study";
import { formatDate } from "@/lib/materials";
import { materialCount, type Collection } from "@/types/collection";

type Tab = "materials" | "chat" | "game" | "diagram";

const TABS = [
  { value: "materials", label: "Materials", icon: <ListAltIcon fontSize="small" /> },
  { value: "chat", label: "Chat", icon: <ForumIcon fontSize="small" /> },
  { value: "game", label: "Game", icon: <SportsEsportsIcon fontSize="small" /> },
  { value: "diagram", label: "Diagrams", icon: <AccountTreeIcon fontSize="small" /> },
];

function Title({ collection }: { collection: Collection }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(collection.name);
  const rename = useRenameCollection(collection.collection_id);

  const save = () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === collection.name) return setEditing(false);
    rename.mutate(trimmed, { onSuccess: () => setEditing(false) });
  };

  if (editing) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <TextField size="small" value={name} autoFocus onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          inputProps={{ "aria-label": "Collection name" }} error={!!rename.error}
          helperText={rename.error ? errorMessage(rename.error) : undefined} />
        <IconButton size="small" onClick={save} aria-label="Save name" disabled={rename.isPending}>
          <CheckIcon fontSize="small" />
        </IconButton>
      </Box>
    );
  }
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, minWidth: 0 }}>
      <Typography variant="h6" fontWeight={700} noWrap title={collection.name}>{collection.name}</Typography>
      <Tooltip title="Rename">
        <IconButton size="small" onClick={() => { setName(collection.name); setEditing(true); }} aria-label="Rename">
          <EditOutlinedIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );
}

export default function CollectionPage({ params }: { params: { collectionId: string } }) {
  const { collectionId } = params;
  const router = useRouter();
  const { data: collection, isPending, error } = useCollection(collectionId);
  const del = useDeleteCollection();
  const [tab, setTab] = useState<Tab>("materials");
  const [picking, setPicking] = useState(false);
  const [confirming, setConfirming] = useState(false);

  if (isPending) {
    return <AppShell><Spinner label="Loading collection…" fullPage /></AppShell>;
  }
  if (!collection) {
    return (
      <AppShell>
        <Box sx={{ p: 4 }}><Alert severity="error">Couldn&apos;t load this collection: {errorMessage(error)}</Alert></Box>
      </AppShell>
    );
  }

  const count = materialCount(collection.materials);
  const unit = collectionUnit(collectionId);

  return (
    <AppShell>
      <StudySessionProvider key={unit} unit={unit} autoGenerate={false}>
        <Box sx={{ display: "flex", height: "calc(100vh - 64px)" }}>
          <Box sx={{ flex: 1, minWidth: 0, overflowY: "auto", borderRight: "1px solid #e9ecef" }}>
            <Box sx={{ p: 3, pb: 1, display: "flex", alignItems: "flex-start", gap: 2 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="caption" color="text.secondary">
                  Collection · {count} {count === 1 ? "item" : "items"} · created {formatDate(collection.created_date)}
                </Typography>
                <Title key={collection.name} collection={collection} />
              </Box>
              <Tooltip title="Delete collection">
                <IconButton onClick={() => setConfirming(true)} aria-label="Delete collection">
                  <DeleteOutlineIcon />
                </IconButton>
              </Tooltip>
            </Box>
            <Divider />
            {count ? (
              <NarrativePanel />
            ) : (
              <Box sx={{ p: 4, textAlign: "center" }}>
                <Typography gutterBottom>This collection is empty.</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Add book sections, transcripts, slides or notes to study them together.
                </Typography>
                <Button variant="contained" onClick={() => setPicking(true)}>Add materials</Button>
              </Box>
            )}
          </Box>

          <Box sx={{ width: 480, flexShrink: 0, display: "flex", flexDirection: "column", bgcolor: "#fff" }}>
            <Tabs items={TABS} value={tab} onChange={(v) => setTab(v as Tab)} variant="fullWidth" />
            <Box sx={{ flex: 1, minHeight: 0, overflowY: tab === "chat" ? "hidden" : "auto" }}>
              {tab === "materials" && <MaterialList collection={collection} onEdit={() => setPicking(true)} />}
              {tab === "chat" && <ChatPanel unit={unit} subject="this collection" />}
              {tab === "game" && <GamePanel />}
              {tab === "diagram" && <DiagramPanel />}
            </Box>
          </Box>
        </Box>
      </StudySessionProvider>

      <MaterialPicker collection={collection} open={picking} onClose={() => setPicking(false)} />

      <Modal
        open={confirming}
        onClose={() => setConfirming(false)}
        title="Delete collection?"
        actions={
          <>
            <Button onClick={() => setConfirming(false)}>Cancel</Button>
            <Button color="error" variant="contained" loading={del.isPending}
              onClick={() => del.mutate(collectionId, { onSuccess: () => router.push("/collections") })}>
              Delete
            </Button>
          </>
        }
      >
        <Typography variant="body2">
          &ldquo;{collection.name}&rdquo;, its study guide and chat history will be removed. The books and
          media in it are kept.
        </Typography>
        {del.error && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(del.error)}</Alert>}
      </Modal>
    </AppShell>
  );
}
