"use client";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { BookDetail } from "@/types/book";
import MobileNav from "./MobileNav";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";

interface Props {
  children: ReactNode;
  /** When set, shows the book's table of contents in a sidebar */
  book?: BookDetail;
  activeSectionId?: string;
  /** Study screens bring their own bottom bar on phones */
  mobileNav?: boolean;
}

export default function AppShell({ children, book, activeSectionId, mobileNav = true }: Props) {
  return (
    <div className="min-h-svh bg-background">
      <TopNav showMenuButton={!!book} />
      <div className="flex">
        {book && <Sidebar book={book} activeSectionId={activeSectionId} />}
        <main className={cn("min-h-[calc(100svh-3.5rem)] min-w-0 flex-1", mobileNav && "max-md:pb-[var(--bottom-bar)]")}>
          {children}
        </main>
      </div>
      {mobileNav && <MobileNav />}
    </div>
  );
}
