import { AlertCircleIcon, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

/** Centered spinner with a label. */
export function LoadingState({ label = "Loading…", fullPage = false, className }: {
  label?: string;
  fullPage?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 p-8 text-sm text-muted-foreground",
        fullPage && "min-h-[calc(100svh-3.5rem)]",
        className,
      )}
    >
      <Spinner className="size-6 text-primary" />
      <span>{label}</span>
    </div>
  );
}

/** Destructive alert with an optional action (e.g. Retry). */
export function ErrorAlert({ title, children, action, className }: {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <Alert variant="destructive" className={className}>
      <AlertCircleIcon />
      {title && <AlertTitle>{title}</AlertTitle>}
      <AlertDescription>
        <div className="flex w-full flex-wrap items-center justify-between gap-2">
          <span className="break-words">{children}</span>
          {action}
        </div>
      </AlertDescription>
    </Alert>
  );
}

/** Empty / placeholder state with an icon, text and optional actions. */
export function EmptyState({ icon: Icon, title, description, children, className }: {
  icon?: LucideIcon;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <Empty className={className}>
      <EmptyHeader>
        {Icon && (
          <EmptyMedia variant="icon">
            <Icon />
          </EmptyMedia>
        )}
        <EmptyTitle>{title}</EmptyTitle>
        {description && <EmptyDescription>{description}</EmptyDescription>}
      </EmptyHeader>
      {children && <EmptyContent>{children}</EmptyContent>}
    </Empty>
  );
}
