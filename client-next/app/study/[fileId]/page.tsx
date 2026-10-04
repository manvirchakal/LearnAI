"use client";
import { Alert, Box, Chip, List, ListItemButton, ListItemText, Typography } from "@mui/material";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { useBook } from "@/api/books";
import { errorMessage } from "@/api/client";

export default function BookOverviewPage({ params }: { params: { fileId: string } }) {
  const { data: book, isPending, error } = useBook(params.fileId);

  return (
    <AppShell book={book}>
      <Box sx={{ p: 4, maxWidth: 900 }}>
        {isPending && <Spinner label="Loading book…" />}
        {error && <Alert severity="error">Couldn&apos;t load this book: {errorMessage(error)}</Alert>}
        {book && (
          <>
            <Typography variant="h5" fontWeight={700}>{book.title}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {book.num_pages} pages · {book.chapter_count} chapters · {book.section_count} sections
            </Typography>
            {book.chapters.map((chapter) => (
              <Card key={chapter.id} sx={{ mb: 2 }} noPadding>
                <Box sx={{ px: 2, pt: 2, display: "flex", alignItems: "center", gap: 1 }}>
                  <Chip size="small" label={chapter.number} />
                  <Typography fontWeight={600}>{chapter.title}</Typography>
                </Box>
                <List dense>
                  {chapter.sections.map((section) => (
                    <ListItemButton key={section.id} component={Link} href={`/study/${book.file_id}/${section.id}`}>
                      <ListItemText
                        primary={section.title}
                        secondary={`Pages ${section.start_page}–${section.end_page}`}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </Card>
            ))}
          </>
        )}
      </Box>
    </AppShell>
  );
}
