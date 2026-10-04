"use client";
import {
  Alert, Box, FormControlLabel, LinearProgress, Paper, Radio, RadioGroup, Step, StepLabel, Stepper, Typography,
} from "@mui/material";
import Link from "next/link";
import { useMemo, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import MarkdownRenderer from "@/components/shared/MarkdownRenderer";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import { useProfile, useQuestionnaire, useSaveProfile } from "@/api/profile";
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
    return <AppShell><Spinner label="Loading…" fullPage /></AppShell>;
  }
  if (questionnaire.error) {
    return (
      <AppShell>
        <Box sx={{ p: 4 }}><Alert severity="error">{errorMessage(questionnaire.error)}</Alert></Box>
      </AppShell>
    );
  }

  const { scale, categories: statements } = questionnaire.data;
  const existing = profile.data;

  if (existing && !retaking) {
    return (
      <AppShell>
        <Box sx={{ p: 4, maxWidth: 760, mx: "auto" }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>Your learning profile</Typography>
          <Card sx={{ mb: 3 }}><MarkdownRenderer content={existing.description} /></Card>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" component={Link} href="/library">Start studying</Button>
            <Button variant="outlined" onClick={() => { setRetaking(true); setStep(0); setAnswers(existing.answers); }}>
              Retake questionnaire
            </Button>
          </Box>
        </Box>
      </AppShell>
    );
  }

  const category = categories[step];
  const current = answers[category] ?? {};
  const stepComplete = statements[category].every((s) => current[s] != null);
  const isLast = step === categories.length - 1;

  const setScore = (statement: string, score: number) =>
    setAnswers((prev) => ({ ...prev, [category]: { ...prev[category], [statement]: score } }));

  const submit = () =>
    save.mutate(answers as ProfileAnswers, { onSuccess: () => setRetaking(false) });

  return (
    <AppShell>
      <Box sx={{ p: 4, maxWidth: 820, mx: "auto" }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>Learning style questionnaire</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Rate how much you agree with each statement. LearnAI uses your answers to tailor every section.
        </Typography>

        <Stepper activeStep={step} sx={{ mb: 3 }} alternativeLabel>
          {categories.map((c) => <Step key={c}><StepLabel>{CATEGORY_LABELS[c]}</StepLabel></Step>)}
        </Stepper>

        {statements[category].map((statement) => (
          <Paper key={statement} variant="outlined" sx={{ p: 2, mb: 1.5 }}>
            <Typography variant="body2" fontWeight={500} gutterBottom>{statement}</Typography>
            <RadioGroup
              row
              value={current[statement] ?? ""}
              onChange={(e) => setScore(statement, Number(e.target.value))}
            >
              {Array.from({ length: scale.max - scale.min + 1 }, (_, i) => scale.min + i).map((score) => (
                <FormControlLabel
                  key={score}
                  value={score}
                  control={<Radio size="small" />}
                  label={<Typography variant="caption">{SCALE_LABELS[score - scale.min] ?? score}</Typography>}
                />
              ))}
            </RadioGroup>
          </Paper>
        ))}

        {save.isPending && <LinearProgress sx={{ my: 2 }} />}
        {save.error && <Alert severity="error" sx={{ my: 2 }}>{errorMessage(save.error)}</Alert>}

        <Box sx={{ display: "flex", justifyContent: "space-between", mt: 2 }}>
          <Button disabled={step === 0} onClick={() => setStep((s) => s - 1)}>Back</Button>
          {isLast ? (
            <Button variant="contained" disabled={!stepComplete} loading={save.isPending} onClick={submit}>
              Save profile
            </Button>
          ) : (
            <Button variant="contained" disabled={!stepComplete} onClick={() => setStep((s) => s + 1)}>Next</Button>
          )}
        </Box>
      </Box>
    </AppShell>
  );
}
