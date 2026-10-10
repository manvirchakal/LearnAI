"use client";
import {
  AudioLinesIcon,
  CalendarIcon,
  ChevronRightIcon,
  FileTextIcon,
  LayersIcon,
  type LucideIcon,
  MicIcon,
  PlaySquareIcon,
  PresentationIcon,
  UploadIcon,
  MonitorPlayIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { EmptyState, ErrorAlert } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { errorMessage } from "@/api/client";
import { useNotesList, usePresentations, useTranscriptions } from "@/api/media";
import { formatDate } from "@/lib/materials";
import { cn } from "@/lib/utils";

const TABS = [
  { value: "transcriptions", label: "Lectures & videos", short: "Lectures", icon: AudioLinesIcon },
  { value: "presentations", label: "Slides", short: "Slides", icon: PresentationIcon },
  { value: "notes", label: "Notes", short: "Notes", icon: FileTextIcon },
] as const;
type Tab = (typeof TABS)[number]["value"];

interface Row {
  key: string;
  href: string;
  icon: LucideIcon;
  /** Tailwind classes for the icon tile */
  tone: string;
  primary: string;
  badge: string;
  meta: string;
  date: string;
}

function RowsSkeleton() {
  return (
    <div className="grid gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 rounded-xl border bg-card p-4 shadow-xs">
          <Skeleton className="size-10 shrink-0 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-2/3 max-w-sm" />
            <Skeleton className="h-3 w-1/3 max-w-40" />
          </div>
        </div>
      ))}
    </div>
  );
}

function Rows({ rows, isPending, error, empty }: {
  rows: Row[];
  isPending: boolean;
  error: unknown;
  empty: { icon: LucideIcon; title: string; description: string };
}) {
  if (isPending) return <RowsSkeleton />;
  if (error) return <ErrorAlert title="Couldn't load media">{errorMessage(error)}</ErrorAlert>;
  if (!rows.length) {
    return (
      <EmptyState
        icon={empty.icon}
        title={empty.title}
        description={empty.description}
        className="rounded-xl border border-dashed bg-card/50"
      >
        <Button asChild size="sm">
          <Link href="/upload">
            <UploadIcon />
            Upload
          </Link>
        </Button>
      </EmptyState>
    );
  }
  return (
    <ul className="grid gap-3">
      {rows.map((r) => (
        <li key={r.key}>
          <Link
            href={r.href}
            className="group flex items-center gap-4 rounded-xl border bg-card p-4 shadow-xs transition-all outline-none hover:border-primary/30 hover:bg-accent/40 hover:shadow-sm focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg ring-1", r.tone)}>
              <r.icon className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{r.primary}</p>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                <Badge variant="secondary" className="font-normal">{r.badge}</Badge>
                {r.meta && <span>{r.meta}</span>}
                {r.date && (
                  <span className="inline-flex items-center gap-1">
                    <CalendarIcon className="size-3" />
                    {r.date}
                  </span>
                )}
              </div>
            </div>
            <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Transcriptions() {
  const { data = [], isPending, error } = useTranscriptions();
  return (
    <Rows
      isPending={isPending}
      error={error}
      empty={{
        icon: AudioLinesIcon,
        title: "No lectures or videos yet",
        description: "Transcribe a recorded lecture or a YouTube video to see it here.",
      }}
      rows={data.map((t) => {
        const yt = t.source_type === "youtube";
        return {
          key: t.job_id,
          href: `/media/transcriptions/${t.job_id}`,
          icon: yt ? MonitorPlayIcon : MicIcon,
          tone: yt ? "bg-destructive/10 text-destructive ring-destructive/15" : "bg-chart-1/10 text-chart-1 ring-chart-1/20",
          primary: t.title,
          badge: yt ? "YouTube" : "Lecture",
          meta: "",
          date: formatDate(t.transcription_date),
        };
      })}
    />
  );
}

function Presentations() {
  const { data = [], isPending, error } = usePresentations();
  return (
    <Rows
      isPending={isPending}
      error={error}
      empty={{
        icon: PresentationIcon,
        title: "No slide decks yet",
        description: "Upload a PowerPoint deck to read its slides and speaker notes here.",
      }}
      rows={data.map((p) => ({
        key: p.presentation_id,
        href: `/media/presentations/${p.presentation_id}`,
        icon: PlaySquareIcon,
        tone: "bg-chart-4/10 text-chart-4 ring-chart-4/20",
        primary: p.original_filename,
        badge: `${p.total_slides} slides`,
        meta: p.has_speaker_notes ? "Speaker notes" : "",
        date: formatDate(p.upload_date),
      }))}
    />
  );
}

function Notes() {
  const { data = [], isPending, error } = useNotesList();
  return (
    <Rows
      isPending={isPending}
      error={error}
      empty={{
        icon: FileTextIcon,
        title: "No notes yet",
        description: "Upload your notes as a document to study from them.",
      }}
      rows={data.map((n) => ({
        key: n.notes_id,
        href: `/media/notes/${n.notes_id}`,
        icon: FileTextIcon,
        tone: "bg-chart-2/10 text-chart-2 ring-chart-2/20",
        primary: n.original_filename,
        badge: n.file_type ? n.file_type.replace(/^\./, "").toUpperCase() : "Notes",
        meta: "",
        date: formatDate(n.upload_date),
      }))}
    />
  );
}

export default function MediaPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const router = useRouter();
  const { tab: tabParam } = use(searchParams);
  const initial = TABS.some((t) => t.value === tabParam) ? (tabParam as Tab) : "transcriptions";
  const [tab, setTab] = useState<Tab>(initial);

  const select = (value: string) => {
    setTab(value as Tab);
    router.replace(`/media?tab=${value}`, { scroll: false });
  };

  return (
    <AppShell>
      <PageContainer className="max-w-4xl">
        <PageHeader
          icon={LayersIcon}
          title="Media"
          description="Transcribed lectures and videos, slide decks and notes."
          actions={
            <Button asChild>
              <Link href="/upload">
                <UploadIcon />
                Upload
              </Link>
            </Button>
          }
        />
        <Tabs value={tab} onValueChange={select} className="gap-4">
          <TabsList className="w-full sm:w-fit">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value} className="sm:px-3">
                <t.icon />
                <span className="sm:hidden">{t.short}</span>
                <span className="hidden sm:inline">{t.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="transcriptions"><Transcriptions /></TabsContent>
          <TabsContent value="presentations"><Presentations /></TabsContent>
          <TabsContent value="notes"><Notes /></TabsContent>
        </Tabs>
      </PageContainer>
    </AppShell>
  );
}
