"use client";
import { ReactNode } from "react";
import type { BookDetail } from "@/types/book";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";

interface Props {
  children: ReactNode;
  /** When set, shows the book's table of contents in a sidebar */
  book?: BookDetail;
  activeSectionId?: string;
}

export default function AppShell({ children, book, activeSectionId }: Props) {
  return (
    <div className="min-h-svh bg-background">
      <TopNav showMenuButton={!!book} />
      <div className="flex">
        {book && <Sidebar book={book} activeSectionId={activeSectionId} />}
        <main className="min-h-[calc(100svh-3.5rem)] min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
