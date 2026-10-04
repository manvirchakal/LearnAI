"use client";
import {
  Alert, Box, Checkbox, FormControl, InputLabel, List, ListItemButton, ListItemIcon, ListItemText, ListSubheader,
  MenuItem, Select, Typography,
} from "@mui/material";
import type { TabsActions } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import Tabs from "@/components/ui/Tabs";
import { useBook, useBooks } from "@/api/books";
import { errorMessage } from "@/api/client";
import { useUpdateCollectionMaterials } from "@/api/collections";
import { useNotesList, usePresentations, useTranscriptions } from "@/api/media";
import { formatDate, hasMaterial, KIND_LABELS, withMaterial, withoutMaterial, type MaterialRef } from "@/lib/materials";
import { MATERIAL_KINDS, materialCount, type Collection, type CollectionMaterials, type MaterialKind } from "@/types/collection";

interface Option {
  ref: MaterialRef;
  primary: string;
  secondary?: string;
}

interface ToggleProps {
  kind: MaterialKind;
  draft: CollectionMaterials;
  onToggle: (kind: MaterialKind, ref: MaterialRef) => void;
}

function OptionList({ kind, options, draft, onToggle, empty }: ToggleProps & { options: Option[]; empty: string }) {
  if (!options.length) return <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>{empty}</Typography>;
  return (
    <List dense disablePadding>
      {options.map((o) => {
        const checked = hasMaterial(draft, kind, o.ref);
        return (
          <ListItemButton key={o.primary + (o.secondary ?? "") + JSON.stringify(o.ref)} onClick={() => onToggle(kind, o.ref)}>
            <ListItemIcon sx={{ minWidth: 36 }}>
              <Checkbox edge="start" size="small" checked={checked} tabIndex={-1} disableRipple
                inputProps={{ "aria-label": o.primary }} />
            </ListItemIcon>
            <ListItemText primary={o.primary} secondary={o.secondary} />
          </ListItemButton>
        );
      })}
    </List>
  );
}

function BookSections(props: ToggleProps) {
  const books = useBooks();
  const [fileId, setFileId] = useState("");
  const book = useBook(fileId);

  useEffect(() => {
    if (!fileId && books.data?.length) setFileId(books.data[0].file_id);
  }, [books.data, fileId]);

  if (books.isPending) return <Spinner size={24} />;
  if (!books.data?.length) {
    return <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>Upload a textbook first.</Typography>;
  }

  return (
    <Box>
      <FormControl size="small" fullWidth sx={{ my: 1 }}>
        <InputLabel id="picker-book">Book</InputLabel>
        <Select labelId="picker-book" label="Book" value={fileId} onChange={(e) => setFileId(e.target.value)}>
          {books.data.map((b) => <MenuItem key={b.file_id} value={b.file_id}>{b.title}</MenuItem>)}
        </Select>
      </FormControl>
      {book.isPending && fileId ? <Spinner size={24} /> : book.data?.chapters.map((chapter) => (
        <List key={chapter.id} dense disablePadding
          subheader={<ListSubheader disableSticky sx={{ lineHeight: "32px" }}>{chapter.number} {chapter.title}</ListSubheader>}>
          <OptionList
            {...props}
            empty=""
            options={chapter.sections.map((s) => ({
              ref: { file_id: book.data.file_id, section_id: s.id, title: `${book.data.title}: ${s.title}` },
              primary: s.title,
              secondary: `pp. ${s.start_page}–${s.end_page}`,
            }))}
          />
        </List>
      ))}
    </Box>
  );
}

function Transcriptions(props: ToggleProps) {
  const { data, isPending } = useTranscriptions();
  if (isPending) return <Spinner size={24} />;
  return (
    <OptionList {...props} empty="No transcribed lectures or videos yet."
      options={(data ?? []).map((t) => ({
        ref: { transcription_id: t.job_id, title: t.title },
        primary: t.title,
        secondary: `${t.source_type === "youtube" ? "YouTube" : "Lecture"} · ${formatDate(t.transcription_date)}`,
      }))} />
  );
}

function Presentations(props: ToggleProps) {
  const { data, isPending } = usePresentations();
  if (isPending) return <Spinner size={24} />;
  return (
    <OptionList {...props} empty="No slide decks yet."
      options={(data ?? []).map((p) => ({
        ref: { presentation_id: p.presentation_id, title: p.original_filename },
        primary: p.original_filename,
        secondary: `${p.total_slides} slides · ${formatDate(p.upload_date)}`,
      }))} />
  );
}

function Notes(props: ToggleProps) {
  const { data, isPending } = useNotesList();
  if (isPending) return <Spinner size={24} />;
  return (
    <OptionList {...props} empty="No notes yet."
      options={(data ?? []).map((n) => ({
        ref: { notes_id: n.notes_id, title: n.original_filename },
        primary: n.original_filename,
        secondary: formatDate(n.upload_date),
      }))} />
  );
}

const PANES: Record<MaterialKind, (p: ToggleProps) => JSX.Element> = {
  textbook_sections: BookSections,
  transcriptions: Transcriptions,
  presentations: Presentations,
  notes: Notes,
};

/** Choose a collection's materials from everything the user has uploaded. */
export default function MaterialPicker({ collection, open, onClose }: {
  collection: Collection;
  open: boolean;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<MaterialKind>("textbook_sections");
  const [draft, setDraft] = useState(collection.materials);
  const update = useUpdateCollectionMaterials();
  const tabsRef = useRef<TabsActions>(null);

  useEffect(() => {
    if (open) setDraft(collection.materials);
  }, [open, collection.materials]);

  // Counts in the tab labels change their widths, which MUI doesn't track
  const counts = MATERIAL_KINDS.map((k) => draft[k].length).join();
  useEffect(() => tabsRef.current?.updateIndicator(), [counts]);

  const toggle = (k: MaterialKind, ref: MaterialRef) =>
    setDraft((d) => (hasMaterial(d, k, ref) ? withoutMaterial(d, k, ref) : withMaterial(d, k, ref)));

  const Pane = PANES[kind];
  const save = () =>
    update.mutate({ collectionId: collection.collection_id, materials: draft }, { onSuccess: onClose });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Choose materials"
      maxWidth="sm"
      fullWidth
      // the tab indicator is measured mid-animation otherwise
      TransitionProps={{ onEntered: () => tabsRef.current?.updateIndicator() }}
      actions={
        <>
          <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
            {materialCount(draft)} selected · changing materials regenerates the study guide
          </Typography>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="contained" onClick={save} loading={update.isPending}>Save</Button>
        </>
      }
    >
      {update.error && <Alert severity="error" sx={{ mb: 1 }}>{errorMessage(update.error)}</Alert>}
      <Tabs
        items={MATERIAL_KINDS.map((k) => ({
          value: k,
          label: draft[k].length ? `${KIND_LABELS[k].many} (${draft[k].length})` : KIND_LABELS[k].many,
        }))}
        value={kind}
        onChange={(v) => setKind(v as MaterialKind)}
        variant="scrollable"
        action={tabsRef}
      />
      <Box sx={{ height: 360, overflowY: "auto", pt: 1 }}>
        <Pane kind={kind} draft={draft} onToggle={toggle} />
      </Box>
    </Modal>
  );
}
