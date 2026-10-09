"use client";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  BookOpenIcon,
  BrainIcon,
  CheckIcon,
  RotateCcwIcon,
  SaveIcon,
} from "lucide-react";
import Link from "next/link";
import { Fragment, useMemo, useState } from "react";
import { toast } from "sonner";
import AppShell from "@/components/layout/AppShell";
import Markdown from "@/components/shared/Markdown";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { ErrorAlert, LoadingState } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useProfile, useQuestionnaire, useSaveProfile } from "@/api/profile";
import { cn } from "@/lib/utils";
import type { ProfileAnswers, VARKCategory } from "@/types/profile";

const CATEGORY_LABELS: Record<VARKCategory, string> = {
  Visual: "Visual",
  Auditory: "Auditory",
  ReadingWriting: "Reading / Writing",
  Kinesthetic: "Kinesthetic",
};
const SCALE_LABELS = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"];

export default function QuestionnairePage() {
  const questionnaire = useQuestionnaire();
  const profile = useProfile();
  const save = useSaveProfile();
  const [retaking, setRetaking] = useState(false);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Partial<ProfileAnswers>>({});

  const categories = useMemo(
    () => (questionnaire.data ? (Object.keys(questionnaire.data.categories) as VARKCategory[]) : []),
    [questionnaire.data],
  );

  if (questionnaire.isPending || profile.isPending) {
    return <AppShell><LoadingState label="Loading…" fullPage /></AppShell>;
  }
  if (questionnaire.error) {
    return (
      <AppShell>
        <PageContainer className="max-w-3xl">
          <ErrorAlert title="Couldn't load the questionnaire">{errorMessage(questionnaire.error)}</ErrorAlert>
        </PageContainer>
      </AppShell>
    );
  }

  const { scale, categories: statements } = questionnaire.data;
  const existing = profile.data;

  if (existing && !retaking) {
    return (
      <AppShell>
        <PageContainer className="max-w-3xl">
          <PageHeader
            icon={BrainIcon}
            title="Your learning profile"
            description="LearnAI uses this profile to tailor every section to how you learn best."
            actions={
              <>
                <Button
                  variant="outline"
                  onClick={() => { setRetaking(true); setStep(0); setAnswers(existing.answers); }}
                >
                  <RotateCcwIcon />
                  Retake questionnaire
                </Button>
                <Button asChild>
                  <Link href="/library">
                    <BookOpenIcon />
                    Start studying
                  </Link>
                </Button>
              </>
            }
          />
          <div className="relative overflow-hidden rounded-xl border bg-card p-6 shadow-xs sm:p-8">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-chart-1 via-chart-2 to-chart-3"
            />
            <Markdown className="text-sm leading-relaxed">{existing.description}</Markdown>
          </div>
        </PageContainer>
      </AppShell>
    );
  }

  const category = categories[step];
  const current = answers[category] ?? {};
  const stepComplete = statements[category].every((s) => current[s] != null);
  const isLast = step === categories.length - 1;

  const totalStatements = categories.reduce((n, c) => n + statements[c].length, 0);
  const answeredStatements = categories.reduce(
    (n, c) => n + statements[c].filter((s) => answers[c]?.[s] != null).length,
    0,
  );
  const scores = Array.from({ length: scale.max - scale.min + 1 }, (_, i) => scale.min + i);

  const setScore = (statement: string, score: number) =>
    setAnswers((prev) => ({ ...prev, [category]: { ...prev[category], [statement]: score } }));

  const submit = () =>
    save.mutate(answers as ProfileAnswers, {
      onSuccess: () => {
        setRetaking(false);
        toast.success("Learning profile saved");
      },
    });

  return (
    <AppShell>
      <PageContainer className="max-w-3xl">
        <PageHeader
          icon={BrainIcon}
          title="Learning style questionnaire"
          description="Rate how much you agree with each statement. LearnAI uses your answers to tailor every section."
        />

        {/* Stepper */}
        <div className="mb-6 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
          <ol className="flex items-center">
            {categories.map((c, i) => {
              const done = i < step;
              const active = i === step;
              return (
                <Fragment key={c}>
                  {i > 0 && (
                    <li aria-hidden className={cn("mx-2 h-px flex-1 transition-colors", i <= step ? "bg-primary" : "bg-border")} />
                  )}
                  <li className="flex min-w-0 shrink-0 flex-col items-center gap-1.5 sm:flex-row sm:gap-2" aria-current={active ? "step" : undefined}>
                    <span
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                        done && "border-primary bg-primary text-primary-foreground",
                        active && "border-primary bg-primary/10 text-primary ring-4 ring-primary/10",
                        !done && !active && "bg-muted text-muted-foreground",
                      )}
                    >
                      {done ? <CheckIcon className="size-3.5" /> : i + 1}
                    </span>
                    <span
                      className={cn(
                        "hidden text-sm font-medium whitespace-nowrap sm:inline",
                        active ? "text-foreground" : "text-muted-foreground",
                      )}
                    >
                      {CATEGORY_LABELS[c]}
                    </span>
                  </li>
                </Fragment>
              );
            })}
          </ol>
          <div className="mt-4 flex items-center gap-3">
            <Progress value={(answeredStatements / Math.max(totalStatements, 1)) * 100} className="h-1.5" />
            <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
              {answeredStatements}/{totalStatements}
            </span>
          </div>
        </div>

        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">{CATEGORY_LABELS[category]}</h2>
          <Badge variant="secondary">Step {step + 1} of {categories.length}</Badge>
        </div>

        <div className="flex flex-col gap-3">
          {statements[category].map((statement, idx) => {
            const value = current[statement];
            const groupId = `q-${step}-${idx}`;
            return (
              <div
                key={statement}
                className={cn(
                  "rounded-xl border bg-card p-4 shadow-xs transition sm:p-5",
                  value != null ? "border-primary/25" : "hover:border-primary/30",
                )}
              >
                <p id={groupId} className="mb-3 text-sm font-medium text-pretty">
                  <span className="mr-2 text-muted-foreground tabular-nums">{idx + 1}.</span>
                  {statement}
                </p>
                <RadioGroup
                  aria-labelledby={groupId}
                  className="grid grid-cols-5 gap-1.5 sm:gap-2"
                  value={value != null ? String(value) : ""}
                  onValueChange={(v) => setScore(statement, Number(v))}
                >
                  {scores.map((score) => {
                    const id = `${groupId}-${score}`;
                    return (
                      <label
                        key={score}
                        htmlFor={id}
                        className="flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-1 py-2 text-center transition hover:bg-accent has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5"
                      >
                        <RadioGroupItem id={id} value={String(score)} />
                        <span className="text-[11px] leading-tight text-muted-foreground sm:text-xs">
                          {SCALE_LABELS[score - scale.min] ?? score}
                        </span>
                      </label>
                    );
                  })}
                </RadioGroup>
              </div>
            );
          })}
        </div>

        {save.error && <ErrorAlert className="mt-4">{errorMessage(save.error)}</ErrorAlert>}

        <div className="mt-6 flex items-center justify-between gap-2">
          <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
            <ArrowLeftIcon />
            Back
          </Button>
          {isLast ? (
            <Button disabled={!stepComplete || save.isPending} onClick={submit}>
              {save.isPending ? <Spinner /> : <SaveIcon />}
              Save profile
            </Button>
          ) : (
            <Button disabled={!stepComplete} onClick={() => setStep((s) => s + 1)}>
              Next
              <ArrowRightIcon />
            </Button>
          )}
        </div>
      </PageContainer>
    </AppShell>
  );
}
