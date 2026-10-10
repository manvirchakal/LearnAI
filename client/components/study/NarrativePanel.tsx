"use client";
import { CheckCircle2Icon, CircleDashedIcon, LoaderCircleIcon, RefreshCwIcon, SparklesIcon } from "lucide-react";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { Shimmer } from "@/components/ai-elements/shimmer";
import Markdown from "@/components/shared/Markdown";
import { ErrorAlert, LoadingState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { STUDY_STEPS, useStudySession } from "./StudySession";

function GenerationProgress() {
  const { completed, activity } = useStudySession();
  const current = STUDY_STEPS.find((s) => !completed.includes(s.stage))?.stage;
  return (
    <ChainOfThought defaultOpen className="mb-6 rounded-xl border bg-card/60 p-4 shadow-xs">
      <ChainOfThoughtHeader>
        <Shimmer as="span" duration={2}>{activity ?? "Working…"}</Shimmer>
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        {STUDY_STEPS.map(({ stage, label }) => {
          const done = completed.includes(stage);
          const active = stage === current;
          return (
            <ChainOfThoughtStep
              key={stage}
              label={label}
              status={done ? "complete" : active ? "active" : "pending"}
              icon={done ? CheckCircle2Icon : active ? LoaderCircleIcon : CircleDashedIcon}
              className={active ? "[&>div:first-child>svg]:animate-spin [&>div:first-child>svg]:text-primary" : undefined}
            />
          );
        })}
      </ChainOfThoughtContent>
    </ChainOfThought>
  );
}

export default function NarrativePanel() {
  const { status, materials, streamingText, error, generate } = useStudySession();

  if (status === "loading") return <LoadingState label="Loading your study guide…" />;

  if (status === "idle") {
    return (
      <div className="flex flex-col items-center px-6 py-16 text-center">
        <span className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-chart-2 text-primary-foreground shadow-lg shadow-primary/20">
          <SparklesIcon className="size-6" />
        </span>
        <h2 className="text-lg font-semibold tracking-tight">Make it yours</h2>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">
          Turn these materials into a personalized narrative, an interactive game and diagrams.
        </p>
        <Button className="mt-5" onClick={() => generate(false)}>
          <SparklesIcon />
          Generate study guide
        </Button>
      </div>
    );
  }

  if (status === "error" && !materials) {
    return (
      <div className="p-6">
        <ErrorAlert
          title="Couldn't generate the study guide"
          action={<Button size="sm" variant="outline" onClick={() => generate(false)}>Retry</Button>}
        >
          {error}
        </ErrorAlert>
      </div>
    );
  }

  const streaming = status === "streaming";
  const text = streaming && streamingText ? streamingText : materials?.narrative ?? "";

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-8">
      {streaming && <GenerationProgress />}
      {status === "error" && <ErrorAlert className="mb-6">{error}</ErrorAlert>}
      {text ? (
        <article className="text-[15px] leading-7">
          <Markdown streaming={streaming}>{text}</Markdown>
        </article>
      ) : (
        <div className="space-y-3">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      )}
      {!streaming && materials && (
        <div className="mt-10 flex justify-center border-t pt-6">
          <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => generate(true)}>
            <RefreshCwIcon />
            Regenerate study guide
          </Button>
        </div>
      )}
    </div>
  );
}
