"use client";
import {
  ArrowRightIcon,
  BrainIcon,
  ChevronRightIcon,
  CloudUploadIcon,
  FolderHeartIcon,
  LibraryIcon,
  MonitorPlayIcon,
  SparklesIcon,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { cn } from "@/lib/utils";

interface Tile {
  href: string;
  icon: LucideIcon;
  title: string;
  desc: string;
  /** Tailwind classes for the icon chip, using chart tokens so dark mode works */
  accent: string;
}

const tiles: Tile[] = [
  {
    href: "/upload",
    icon: CloudUploadIcon,
    title: "Upload Material",
    desc: "Add PDFs, YouTube videos, lectures, slides or notes.",
    accent: "bg-chart-1/10 text-chart-1 ring-chart-1/20",
  },
  {
    href: "/library",
    icon: LibraryIcon,
    title: "My Library",
    desc: "Browse and study your uploaded textbooks.",
    accent: "bg-chart-2/10 text-chart-2 ring-chart-2/20",
  },
  {
    href: "/collections",
    icon: FolderHeartIcon,
    title: "Collections",
    desc: "Study sections, lectures and slides together.",
    accent: "bg-chart-3/10 text-chart-3 ring-chart-3/20",
  },
  {
    href: "/media",
    icon: MonitorPlayIcon,
    title: "Media",
    desc: "Your transcripts, slide decks and notes.",
    accent: "bg-chart-4/10 text-chart-4 ring-chart-4/20",
  },
  {
    href: "/questionnaire",
    icon: BrainIcon,
    title: "Learning Profile",
    desc: "Discover your VARK learning style.",
    accent: "bg-chart-5/10 text-chart-5 ring-chart-5/20",
  },
];

export default function HomePage() {
  return (
    <AppShell>
      <PageContainer>
        <div className="relative mb-6 overflow-hidden rounded-2xl border bg-card p-5 shadow-xs sm:mb-8 sm:p-8">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-chart-2/10"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -right-24 size-64 rounded-full bg-primary/10 blur-3xl"
          />
          <PageHeader
            className="relative mb-0"
            icon={SparklesIcon}
            eyebrow="Your AI study companion"
            title="Welcome to LearnAI"
            description="Upload your study material and let AI tailor the experience to your learning style."
          />
        </div>

        {/* Phones: compact rows; larger screens: cards */}
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
          {tiles.map(({ href, icon: Icon, title, desc, accent }) => (
            <Link
              key={href}
              href={href}
              className="group flex items-center gap-4 rounded-xl border bg-card p-4 shadow-xs transition outline-none active:scale-[0.99] sm:flex-col sm:items-stretch sm:p-5 sm:hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl ring-1", accent)}>
                <Icon className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold tracking-tight">{title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
              </div>
              <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground sm:hidden" />
              <span className="hidden items-center gap-1 text-sm font-medium text-primary sm:inline-flex">
                Open
                <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </PageContainer>
    </AppShell>
  );
}
