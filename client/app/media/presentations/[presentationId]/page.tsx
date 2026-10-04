"use client";
import { Box, Typography } from "@mui/material";
import MediaDetail from "@/components/media/MediaDetail";
import Card from "@/components/ui/Card";
import { usePresentation } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function PresentationPage({ params }: { params: { presentationId: string } }) {
  const { data, isPending, error } = usePresentation(params.presentationId);
  const meta = data?.metadata;

  return (
    <MediaDetail
      tab="presentations"
      isPending={isPending}
      error={error}
      title={meta?.original_filename}
      subtitle={meta && `${meta.total_slides} slides · uploaded ${formatDate(meta.upload_date)}`}
      kind="presentations"
      item={meta && { presentation_id: meta.presentation_id, title: meta.original_filename }}
      collectionId={meta?.collection_id}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {data?.slides.map((slide, i) => (
          <Card key={i}>
            <Typography variant="caption" color="text.secondary">Slide {i + 1}</Typography>
            <Typography fontWeight={600} gutterBottom>{slide.title || "Untitled slide"}</Typography>
            {slide.content.filter((c) => c !== slide.title).map((text, j) => (
              <Typography key={j} variant="body2" sx={{ whiteSpace: "pre-wrap", mb: 0.5 }}>{text}</Typography>
            ))}
            {slide.notes && (
              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "#f8f9fa", borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Speaker notes</Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{slide.notes}</Typography>
              </Box>
            )}
          </Card>
        ))}
      </Box>
    </MediaDetail>
  );
}
