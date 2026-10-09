import { ArrowRightIcon, CheckCircle2Icon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

/** Success message with an optional "view result" link, shared by the upload widgets. */
export default function SuccessAlert({ children, href, linkLabel, className }: {
  children: ReactNode;
  href?: string;
  linkLabel?: string;
  className?: string;
}) {
  return (
    <Alert className={cn("border-chart-3/30 bg-chart-3/5 [&>svg]:text-chart-3", className)}>
      <CheckCircle2Icon />
      <AlertDescription className="text-foreground">
        <div className="flex w-full flex-wrap items-center justify-between gap-2">
          <span className="break-words">{children}</span>
          {href && (
            <Link
              href={href}
              className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
            >
              {linkLabel}
              <ArrowRightIcon className="size-3.5" />
            </Link>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
