"use client";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import Link from "next/link";
import { useState } from "react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import { useDeleteBook } from "@/api/books";
import type { BookSummary } from "@/types/book";

export default function BookCard({ book }: { book: BookSummary }) {
  const [confirming, setConfirming] = useState(false);
  const del = useDeleteBook();

  return (
    <>
      <Card
        sx={{
          height: "100%",
          transition: "transform 0.15s, box-shadow 0.15s",
          "&:hover": { transform: "translateY(-2px)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" },
        }}
      >
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
          <Link href={`/study/${book.file_id}`} style={{ display: "flex", gap: 16, flex: 1, minWidth: 0, color: "inherit", textDecoration: "none" }}>
            <Box sx={{ width: 48, height: 64, bgcolor: "#eff6ff", borderRadius: 1, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <MenuBookIcon sx={{ color: "primary.main", fontSize: 24 }} />
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography fontWeight={600} variant="body2" noWrap title={book.title}>{book.title}</Typography>
              <Box sx={{ mt: 0.5, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                <Badge label={`${book.num_pages} pages`} />
                <Badge tone="primary" label={`${book.section_count} sections`} />
              </Box>
            </Box>
          </Link>
          <Tooltip title="Delete">
            <IconButton size="small" onClick={() => setConfirming(true)} aria-label={`Delete ${book.title}`}>
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Card>

      <Modal
        open={confirming}
        onClose={() => setConfirming(false)}
        title="Delete book?"
        actions={
          <>
            <Button onClick={() => setConfirming(false)}>Cancel</Button>
            <Button
              color="error"
              variant="contained"
              loading={del.isPending}
              onClick={() => del.mutate(book.file_id, { onSuccess: () => setConfirming(false) })}
            >
              Delete
            </Button>
          </>
        }
      >
        <Typography variant="body2">
          &ldquo;{book.title}&rdquo; and its generated study materials and chat history will be removed.
        </Typography>
      </Modal>
    </>
  );
}
