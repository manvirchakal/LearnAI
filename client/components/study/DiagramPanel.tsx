"use client";
import { WorkflowIcon } from "lucide-react";
import Markdown from "@/components/shared/Markdown";
import { EmptyState, LoadingState } from "@/components/shared/States";
import { NotYet, useStudySession } from "./StudySession";

export default function DiagramPanel() {
  const { status, materials, activity } = useStudySession();

  if (!materials) {
    if (status === "idle") return <NotYet />;
    return status === "error"
      ? <EmptyState icon={WorkflowIcon} title="Diagrams unavailable" />
      : <LoadingState label={activity ?? "Generating diagrams…"} />;
  }

  if (materials.diagrams.length === 0) {
    return <EmptyState icon={WorkflowIcon} title="No diagrams" description="None were generated for this material." />;
  }

  return (
    <div className="space-y-4 p-4">
      {materials.diagrams.map((diagram, i) => (
        <figure key={i} className="overflow-hidden rounded-xl border bg-card shadow-xs">
          <figcaption className="border-b px-4 py-2 text-xs font-medium text-muted-foreground">Diagram {i + 1}</figcaption>
          <div className="overflow-x-auto p-3">
            <Markdown>{"```mermaid\n" + diagram.trim() + "\n```"}</Markdown>
          </div>
        </figure>
      ))}
    </div>
  );
}
