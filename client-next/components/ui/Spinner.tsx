"use client";
import { Box, CircularProgress, Typography } from "@mui/material";

interface Props {
  size?: number;
  label?: string;
  fullPage?: boolean;
}

export default function Spinner({ size = 40, label, fullPage }: Props) {
  const inner = (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5 }}>
      <CircularProgress size={size} />
      {label && <Typography variant="body2" color="text.secondary">{label}</Typography>}
    </Box>
  );

  if (fullPage) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        {inner}
      </Box>
    );
  }

  return inner;
}
