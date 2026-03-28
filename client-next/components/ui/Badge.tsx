"use client";
import { Chip, ChipProps } from "@mui/material";

interface Props extends Omit<ChipProps, "color"> {
  variant?: "default" | "primary" | "success" | "warning" | "error";
}

const colorMap = {
  default: { bgcolor: "#f1f3f5", color: "#495057" },
  primary: { bgcolor: "#e7f0fd", color: "#1d6ce0" },
  success: { bgcolor: "#d3f9d8", color: "#2f9e44" },
  warning: { bgcolor: "#fff3bf", color: "#e67700" },
  error: { bgcolor: "#ffe3e3", color: "#c92a2a" },
};

export default function Badge({ variant = "default", sx, ...props }: Props) {
  const colors = colorMap[variant];
  return (
    <Chip
      size="small"
      sx={{ fontWeight: 500, fontSize: 11, height: 20, ...colors, ...sx }}
      {...props}
    />
  );
}
