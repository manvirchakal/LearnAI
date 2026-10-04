"use client";
import { Card as MuiCard, CardContent, CardProps, SxProps, Theme } from "@mui/material";
import { ReactNode } from "react";

interface Props extends CardProps {
  children: ReactNode;
  contentSx?: SxProps<Theme>;
  noPadding?: boolean;
}

export default function Card({ children, contentSx, noPadding, sx, ...props }: Props) {
  return (
    <MuiCard
      sx={{ borderRadius: 2, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", border: "1px solid #e9ecef", ...sx }}
      elevation={0}
      {...props}
    >
      <CardContent sx={noPadding ? { p: 0, "&:last-child": { pb: 0 } } : contentSx}>
        {children}
      </CardContent>
    </MuiCard>
  );
}
