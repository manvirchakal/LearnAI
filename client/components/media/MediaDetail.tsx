"use client";
import { ArrowLeftIcon, GraduationCapIcon, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { ReactNode } from "react";
import AddToCollectionButton from "@/components/collections/AddToCollectionButton";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage } from "@/api/client";
import type { MaterialRef } from "@/lib/materials";
import type { MaterialKind } from "@/types/collection";

interface Props {
  tab: string;
  isPending: boolean;
  error: unknown;
  title?: string;
  subtitle?: ReactNode;
  /** Icon shown next to the title */
  icon?: LucideIcon;
  /** Small label above the title (e.g. a source badge) */
  eyebrow?: ReactNode;
  kind: MaterialKind;
  item?: MaterialRef;
  /** The collection created for this upload alone, for studying it by itself */
  collectionId?: string;
  children?: ReactNode;
}

function DetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading">
      <div className="mb-8 flex items-start gap-3">
        <Skeleton className="size-10 shrink-0 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-7 w-3/4 max-w-md" />
          <Skeleton className="h-4 w-1/2 max-w-xs" />
        </div>
      </div>
      <div className="space-y-3 rounded-xl border bg-card p-6 shadow-xs">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-4" style={{ width: `${95 - ((i * 17) % 35)}%` }} />
        ))}
      </div>
    </div>
  );
}

/** Shared frame for a single transcript, slide deck or notes page. */
export default function MediaDetail({
  tab, isPending, error, title, subtitle, icon, eyebrow, kind, item, collectionId, children,
}: Props) {
  return (
    <AppShell>
      <PageContainer className="max-w-4xl">
        <Button asChild variant="ghost" size="sm" className="mb-4 -ml-2 text-muted-foreground hover:text-foreground">
          <Link href={`/media?tab=${tab}`}>
            <ArrowLeftIcon />
            Media
          </Link>
        </Button>
        {isPending && <DetailSkeleton />}
        {!isPending && error != null && (
          <ErrorAlert title="Couldn't load this item">{errorMessage(error)}</ErrorAlert>
        )}
        {!isPending && title && (
          <>
            <PageHeader
              icon={icon}
              eyebrow={eyebrow}
              title={<span className="break-words">{title}</span>}
              description={subtitle}
              actions={
                (collectionId || item) && (
                  <>
                    {collectionId && (
                      <Button asChild size="sm">
                        <Link href={`/collections/${collectionId}`}>
                          <GraduationCapIcon />
                          Study
                        </Link>
                      </Button>
                    )}
                    {item && <AddToCollectionButton kind={kind} item={item} />}
                  </>
                )
              }
            />
            {children}
          </>
        )}
      </PageContainer>
    </AppShell>
  );
}
