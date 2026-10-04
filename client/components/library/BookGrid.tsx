"use client";
import { Box, Typography } from "@mui/material";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import BookCard from "./BookCard";
import type { BookSummary } from "@/types/book";

interface Props {
  books: BookSummary[];
}

export default function BookGrid({ books }: Props) {
  if (books.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <MenuBookIcon sx={{ fontSize: 60, color: "text.disabled", mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No books yet
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Upload a PDF to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        gap: 2,
      }}
    >
      {books.map((book, i) => (
        <BookCard key={book.file_id} book={book} />
      ))}
    </Box>
  );
}
