"use client";
import { Box, Typography } from "@mui/material";
import AppShell from "@/components/layout/AppShell";
import BookGrid from "@/components/library/BookGrid";
import Spinner from "@/components/ui/Spinner";
import { useUserBooks } from "@/api/textbooks";

export default function LibraryPage() {
  const { data, isLoading, error } = useUserBooks();
  const books = Array.isArray(data) ? data : [];

  return (
    <AppShell>
      <Box sx={{ p: 4 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>My Library</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {books.length} {books.length === 1 ? "item" : "items"}
        </Typography>

        {isLoading && <Spinner label="Loading library…" />}
        {error && <Typography color="error">Failed to load library.</Typography>}
        {!isLoading && <BookGrid books={books} />}
      </Box>
    </AppShell>
  );
}
