"use client";
import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import type { BookItem } from "@/types/textbook";
import { useRouter } from "next/navigation";

interface Props {
  book: BookItem;
}

export default function BookCard({ book }: Props) {
  const router = useRouter();

  const handleOpen = () => {
    router.push(`/study/${book.file_id}/${encodeURIComponent(book.title)}`);
  };

  return (
    <Card
      sx={{
        cursor: "pointer",
        transition: "transform 0.15s, box-shadow 0.15s",
        "&:hover": { transform: "translateY(-2px)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" },
      }}
      onClick={handleOpen}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
        <Box
          sx={{
            width: 48,
            height: 64,
            bgcolor: "primary.50",
            borderRadius: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <MenuBookIcon sx={{ color: "primary.main", fontSize: 24 }} />
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            fontWeight={600}
            variant="body2"
            sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          >
            {book.title}
          </Typography>
          {book.author && (
            <Typography variant="caption" color="text.secondary" display="block">
              {book.author}
            </Typography>
          )}
          <Box sx={{ mt: 0.5 }}>
            <Badge label={`${book.num_pages ?? "?"} pages`} />
          </Box>
        </Box>

        <Tooltip title="Open">
          <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleOpen(); }}>
            <ArrowForwardIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Card>
  );
}
