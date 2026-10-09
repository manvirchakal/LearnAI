"use client";
import { RotateCcwIcon, TriangleAlertIcon } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { EmptyState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <AppShell>
      <EmptyState
        className="min-h-[calc(100svh-3.5rem)]"
        icon={TriangleAlertIcon}
        title="Something went wrong"
        description={error.message}
      >
        <Button variant="outline" onClick={reset}>
          <RotateCcwIcon />
          Try again
        </Button>
      </EmptyState>
    </AppShell>
  );
}
