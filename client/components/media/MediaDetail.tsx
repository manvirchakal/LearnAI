"use client";
import { Alert, Box, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SchoolIcon from "@mui/icons-material/School";
import Link from "next/link";
import { ReactNode } from "react";
import AddToCollectionButton from "@/components/collections/AddToCollectionButton";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import type { MaterialRef } from "@/lib/materials";
import type { MaterialKind } from "@/types/collection";

interface Props {
  tab: string;
  isPending: boolean;
  error: unknown;
  title?: string;
  subtitle?: ReactNode;
  kind: MaterialKind;
  item?: MaterialRef;
  /** The collection created for this upload alone, for studying it by itself */
  collectionId?: string;
  children?: ReactNode;
}

/** Shared frame for a single transcript, slide deck or notes page. */
export default function MediaDetail({ tab, isPending, error, title, subtitle, kind, item, collectionId, children }: Props) {
  return (
    <AppShell>
      <Box sx={{ p: 4, maxWidth: 900, mx: "auto" }}>
        <Link href={`/media?tab=${tab}`} style={{ textDecoration: "none" }}>
          <Button size="small" startIcon={<ArrowBackIcon fontSize="small" />} sx={{ mb: 2, ml: -1 }}>Media</Button>
        </Link>
        {isPending && <Spinner label="Loading…" />}
        {!isPending && error != null && <Alert severity="error">{errorMessage(error)}</Alert>}
        {!isPending && title && (
          <>
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 3, flexWrap: "wrap" }}>
              <Box sx={{ flex: 1, minWidth: 240 }}>
                <Typography variant="h5" fontWeight={700} sx={{ wordBreak: "break-word" }}>{title}</Typography>
                {subtitle && <Typography variant="body2" color="text.secondary">{subtitle}</Typography>}
              </Box>
              <Box sx={{ display: "flex", gap: 1 }}>
                {collectionId && (
                  <Link href={`/collections/${collectionId}`} style={{ textDecoration: "none" }}>
                    <Button size="small" variant="contained" startIcon={<SchoolIcon fontSize="small" />}>Study</Button>
                  </Link>
                )}
                {item && <AddToCollectionButton kind={kind} item={item} />}
              </Box>
            </Box>
            {children}
          </>
        )}
      </Box>
    </AppShell>
  );
}
