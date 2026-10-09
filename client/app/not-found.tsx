import { CompassIcon } from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import { EmptyState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <AppShell>
      <EmptyState
        className="min-h-[calc(100svh-3.5rem)]"
        icon={CompassIcon}
        title="Page not found"
        description="That page doesn't exist or has moved."
      >
        <Button asChild>
          <Link href="/home">Go home</Link>
        </Button>
      </EmptyState>
    </AppShell>
  );
}
