"use client";
import {
  BookOpenIcon,
  CloudUploadIcon,
  MicIcon,
  NotebookPenIcon,
  PresentationIcon,
  MonitorPlayIcon,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import FileUploadZone from "@/components/upload/FileUploadZone";
import LectureRecorder from "@/components/upload/LectureRecorder";
import NotesUpload from "@/components/upload/NotesUpload";
import PresentationUpload from "@/components/upload/PresentationUpload";
import YouTubeInput from "@/components/upload/YouTubeInput";
import { cn } from "@/lib/utils";

function UploadSection({ icon: Icon, title, description, accent, children }: {
  icon: LucideIcon;
  title: string;
  description: string;
  accent: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border bg-card shadow-xs transition hover:border-primary/30 hover:shadow-md">
      <header className="flex items-start gap-3 border-b px-5 py-4">
        <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg ring-1", accent)}>
          <Icon className="size-4.5" />
        </span>
        <div className="min-w-0">
          <h2 className="font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

export default function UploadPage() {
  return (
    <AppShell>
      <PageContainer className="max-w-3xl">
        <PageHeader
          icon={CloudUploadIcon}
          title="Upload Material"
          description="Add textbooks, lectures, slides or notes to your library."
        />

        <div className="flex flex-col gap-6">
          <UploadSection
            icon={BookOpenIcon}
            title="PDF Textbook"
            description="Chapters and sections are detected automatically."
            accent="bg-primary/10 text-primary ring-primary/20"
          >
            <FileUploadZone />
          </UploadSection>

          <UploadSection
            icon={MonitorPlayIcon}
            title="Online Sources"
            description="Paste a YouTube link to get a full transcript."
            accent="bg-chart-5/10 text-chart-5 ring-chart-5/20"
          >
            <YouTubeInput />
          </UploadSection>

          <UploadSection
            icon={MicIcon}
            title="Record a Lecture"
            description="Record audio in the browser and transcribe it."
            accent="bg-destructive/10 text-destructive ring-destructive/20"
          >
            <LectureRecorder />
          </UploadSection>

          <UploadSection
            icon={PresentationIcon}
            title="Presentation Slides"
            description="Upload a PowerPoint deck."
            accent="bg-chart-4/10 text-chart-4 ring-chart-4/20"
          >
            <PresentationUpload />
          </UploadSection>

          <UploadSection
            icon={NotebookPenIcon}
            title="Notes"
            description="Upload your own notes."
            accent="bg-chart-3/10 text-chart-3 ring-chart-3/20"
          >
            <NotesUpload />
          </UploadSection>
        </div>
      </PageContainer>
    </AppShell>
  );
}
