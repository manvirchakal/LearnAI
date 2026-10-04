"use client";
import { Alert, Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import MicIcon from "@mui/icons-material/Mic";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import YouTubeIcon from "@mui/icons-material/YouTube";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import Tabs from "@/components/ui/Tabs";
import { errorMessage } from "@/api/client";
import { useNotesList, usePresentations, useTranscriptions } from "@/api/media";
import { formatDate } from "@/lib/materials";

const TABS = [
  { value: "transcriptions", label: "Lectures & videos" },
  { value: "presentations", label: "Slides" },
  { value: "notes", label: "Notes" },
] as const;
type Tab = (typeof TABS)[number]["value"];

interface Row {
  key: string;
  href: string;
  icon: ReactNode;
  primary: string;
  secondary: string;
}

function Rows({ rows, isPending, error, empty }: { rows: Row[]; isPending: boolean; error: unknown; empty: string }) {
  if (isPending) return <Box sx={{ p: 3 }}><Spinner size={28} /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 2 }}>{errorMessage(error)}</Alert>;
  if (!rows.length) return <Typography color="text.secondary" variant="body2" sx={{ p: 3, textAlign: "center" }}>{empty}</Typography>;
  return (
    <List disablePadding>
      {rows.map((r) => (
        <ListItemButton key={r.key} component={Link} href={r.href} divider>
          <ListItemIcon sx={{ minWidth: 40 }}>{r.icon}</ListItemIcon>
          <ListItemText primary={r.primary} secondary={r.secondary} primaryTypographyProps={{ fontWeight: 500 }} />
        </ListItemButton>
      ))}
    </List>
  );
}

function Transcriptions() {
  const { data = [], isPending, error } = useTranscriptions();
  return (
    <Rows isPending={isPending} error={error} empty="No lectures or videos transcribed yet."
      rows={data.map((t) => ({
        key: t.job_id,
        href: `/media/transcriptions/${t.job_id}`,
        icon: t.source_type === "youtube" ? <YouTubeIcon sx={{ color: "#ff0000" }} /> : <MicIcon color="error" />,
        primary: t.title,
        secondary: `${t.source_type === "youtube" ? "YouTube" : "Lecture"} · ${formatDate(t.transcription_date)}`,
      }))} />
  );
}

function Presentations() {
  const { data = [], isPending, error } = usePresentations();
  return (
    <Rows isPending={isPending} error={error} empty="No slide decks uploaded yet."
      rows={data.map((p) => ({
        key: p.presentation_id,
        href: `/media/presentations/${p.presentation_id}`,
        icon: <SlideshowIcon color="warning" />,
        primary: p.original_filename,
        secondary: `${p.total_slides} slides · ${formatDate(p.upload_date)}`,
      }))} />
  );
}

function Notes() {
  const { data = [], isPending, error } = useNotesList();
  return (
    <Rows isPending={isPending} error={error} empty="No notes uploaded yet."
      rows={data.map((n) => ({
        key: n.notes_id,
        href: `/media/notes/${n.notes_id}`,
        icon: <DescriptionOutlinedIcon color="success" />,
        primary: n.original_filename,
        secondary: formatDate(n.upload_date),
      }))} />
  );
}

export default function MediaPage({ searchParams }: { searchParams: { tab?: string } }) {
  const router = useRouter();
  const initial = TABS.some((t) => t.value === searchParams.tab) ? (searchParams.tab as Tab) : "transcriptions";
  const [tab, setTab] = useState<Tab>(initial);

  const select = (value: string) => {
    setTab(value as Tab);
    router.replace(`/media?tab=${value}`, { scroll: false });
  };

  return (
    <AppShell>
      <Box sx={{ p: 4, maxWidth: 900, mx: "auto" }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 3 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" fontWeight={700} gutterBottom>Media</Typography>
            <Typography variant="body2" color="text.secondary">
              Transcribed lectures and videos, slide decks and notes.
            </Typography>
          </Box>
          <Link href="/upload" style={{ textDecoration: "none" }}>
            <Button variant="contained" startIcon={<CloudUploadIcon />}>Upload</Button>
          </Link>
        </Box>
        <Card noPadding>
          <Tabs items={[...TABS]} value={tab} onChange={select} />
          {tab === "transcriptions" && <Transcriptions />}
          {tab === "presentations" && <Presentations />}
          {tab === "notes" && <Notes />}
        </Card>
      </Box>
    </AppShell>
  );
}
