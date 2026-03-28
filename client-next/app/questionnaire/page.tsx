"use client";
import {
  Box, Typography, Radio, RadioGroup, FormControlLabel,
  FormControl, FormLabel, Stepper, Step, StepLabel, Alert,
} from "@mui/material";
import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/ui/Button";
import { useSaveProfile } from "@/api/profile";
import { useRouter } from "next/navigation";

const QUESTIONS = [
  {
    id: "q1",
    category: "Visual" as const,
    text: "When learning something new, you prefer:",
    options: [
      { value: "V", label: "Diagrams, charts, and visual representations" },
      { value: "A", label: "Listening to an explanation or lecture" },
      { value: "R", label: "Reading detailed written instructions" },
      { value: "K", label: "Trying it hands-on immediately" },
    ],
  },
  {
    id: "q2",
    category: "Auditory" as const,
    text: "When you need to remember something important, you:",
    options: [
      { value: "V", label: "Visualize it in your mind" },
      { value: "A", label: "Repeat it aloud or discuss it" },
      { value: "R", label: "Write it down in notes" },
      { value: "K", label: "Associate it with a physical experience" },
    ],
  },
  {
    id: "q3",
    category: "ReadingWriting" as const,
    text: "When solving a complex problem, you prefer to:",
    options: [
      { value: "V", label: "Draw a diagram or flowchart" },
      { value: "A", label: "Talk through the steps with someone" },
      { value: "R", label: "Research and read relevant materials" },
      { value: "K", label: "Jump in and experiment" },
    ],
  },
  {
    id: "q4",
    category: "Kinesthetic" as const,
    text: "In class or training, you learn best when:",
    options: [
      { value: "V", label: "There are plenty of visuals and demonstrations" },
      { value: "A", label: "There is discussion and verbal explanation" },
      { value: "R", label: "You receive handouts and can read at your own pace" },
      { value: "K", label: "There are practical exercises and activities" },
    ],
  },
];

type VARKCode = "V" | "A" | "R" | "K";

export default function QuestionnairePage() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, VARKCode>>({});
  const router = useRouter();
  const { mutate: save, isPending, error, isSuccess } = useSaveProfile();

  const current = QUESTIONS[step];
  const selected = answers[current.id];

  const handleNext = () => {
    if (step < QUESTIONS.length - 1) {
      setStep((s) => s + 1);
    } else {
      // Submit
      const counts: Record<string, number> = { V: 0, A: 0, R: 0, K: 0 };
      Object.values(answers).forEach((v) => { counts[v] = (counts[v] || 0) + 1; });
      save(
        { answers: { Visual: { score: counts.V }, Auditory: { score: counts.A }, ReadingWriting: { score: counts.R }, Kinesthetic: { score: counts.K } } },
        { onSuccess: () => setTimeout(() => router.push("/home"), 1500) }
      );
    }
  };

  if (isSuccess) {
    return (
      <AppShell>
        <Box sx={{ p: 4, maxWidth: 600, mx: "auto", textAlign: "center" }}>
          <Alert severity="success" sx={{ mb: 3 }}>Profile saved! Redirecting…</Alert>
        </Box>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Box sx={{ p: 4, maxWidth: 640, mx: "auto" }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>Learning Style Questionnaire</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Answer a few questions so LearnAI can personalize your experience.
        </Typography>

        <Stepper activeStep={step} sx={{ mb: 4 }}>
          {QUESTIONS.map((q) => (
            <Step key={q.id}><StepLabel /></Step>
          ))}
        </Stepper>

        <FormControl component="fieldset" fullWidth>
          <FormLabel component="legend" sx={{ fontWeight: 600, color: "text.primary", mb: 2, fontSize: 16 }}>
            {current.text}
          </FormLabel>
          <RadioGroup value={selected || ""} onChange={(e) => setAnswers({ ...answers, [current.id]: e.target.value as VARKCode })}>
            {current.options.map((opt) => (
              <FormControlLabel
                key={opt.value}
                value={opt.value}
                control={<Radio />}
                label={opt.label}
                sx={{
                  mb: 1,
                  p: 1.5,
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: selected === opt.value ? "primary.main" : "#e9ecef",
                  bgcolor: selected === opt.value ? "primary.50" : "white",
                  transition: "all 0.15s",
                }}
              />
            ))}
          </RadioGroup>
        </FormControl>

        {error && <Alert severity="error" sx={{ mt: 2 }}>Failed to save profile.</Alert>}

        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
          <Button
            variant="contained"
            disabled={!selected}
            loading={isPending}
            onClick={handleNext}
          >
            {step < QUESTIONS.length - 1 ? "Next" : "Finish"}
          </Button>
        </Box>
      </Box>
    </AppShell>
  );
}
