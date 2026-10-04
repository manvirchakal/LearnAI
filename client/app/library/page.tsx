"use client";
import { Alert, Box, Typography } from "@mui/material";
import AppShell from "@/components/layout/AppShell";
import BookGrid from "@/components/library/BookGrid";
import Spinner from "@/components/ui/Spinner";
import { useBooks } from "@/api/books";
import { errorMessage } from "@/api/client";

export default function LibraryPage() {
  const { data: books = [], isPending, error } = useBooks();

  return (
    <AppShell>
      <Box sx={{ p: 4 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>My Library</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {books.length} {books.length === 1 ? "book" : "books"}
        </Typography>
        {isPending && <Spinner label="Loading library…" />}
        {error && <Alert severity="error">Failed to load library: {errorMessage(error)}</Alert>}
        {!isPending && !error && <BookGrid books={books} />}
      </Box>
    </AppShell>
  );
}
