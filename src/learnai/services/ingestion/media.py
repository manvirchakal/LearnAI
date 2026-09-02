"""Lecture audio/video ingestion — turns an ``ASREngine`` transcript into
the same ``TOCResult``/``SectionContent`` shape a PDF's TOC pass produces,
so a transcribed lecture flows through collections/generation/chat with
no changes to any of that code (see ``repositories/materials.py``'s
module docstring for the ``kind`` field this backs).

Segments are grouped into coarse time buckets rather than kept as one
giant section or as one node per whisper segment (which can be only a
few words) — bucketing keeps each section a reasonable retrieval/reading
unit, the same role a PDF chapter plays.
"""

from __future__ import annotations

from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.services.asr import TranscriptResult, TranscriptSegment

# Content types accepted for a direct lecture upload — faster-whisper
# decodes any of these itself (via PyAV/ffmpeg internally), so no
# transcoding step is needed before transcription, unlike the old
# design's raw ffmpeg subprocess call.
ALLOWED_LECTURE_CONTENT_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp4",
        "audio/x-m4a",
        "audio/wav",
        "audio/x-wav",
        "video/mp4",
    }
)

# Coarse enough to keep each section a reasonable reading/retrieval unit
# (comparable to a PDF chapter), fine enough that "jump to this part"
# still means something on an hour-long lecture.
_BUCKET_SECONDS = 5 * 60


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _bucket_segments(segments: list[TranscriptSegment]) -> list[list[TranscriptSegment]]:
    buckets: list[list[TranscriptSegment]] = []
    current: list[TranscriptSegment] = []
    bucket_start = segments[0].start
    for segment in segments:
        if segment.start - bucket_start >= _BUCKET_SECONDS and current:
            buckets.append(current)
            current = []
            bucket_start = segment.start
        current.append(segment)
    if current:
        buckets.append(current)
    return buckets


def group_transcript_into_tree(
    transcript: TranscriptResult, *, title: str
) -> tuple[TOCResult, list[SectionContent]]:
    if not transcript.segments:
        return TOCResult(tree=[], confidence="low", notes="no speech detected"), []

    nodes: list[TreeNode] = []
    sections: list[SectionContent] = []
    for index, bucket in enumerate(_bucket_segments(transcript.segments), start=1):
        start_label = _format_timestamp(bucket[0].start)
        end_label = _format_timestamp(bucket[-1].end)
        node_id = str(index)
        nodes.append(
            TreeNode(
                node_id=node_id,
                title=f"{title} ({start_label}-{end_label})",
                # Not real page numbers — lecture materials have no pages.
                # Reused as an approximate minute marker (this bucket's
                # start) so citations still show something roughly
                # meaningful ("p.12" ~ "~12 minutes in") without a schema
                # change for time-based content.
                start_page=int(bucket[0].start // 60) + 1,
                end_page=int(bucket[-1].end // 60) + 1,
            )
        )
        sections.append(SectionContent(node_id=node_id, text=" ".join(s.text for s in bucket)))
    return TOCResult(tree=nodes, confidence="high"), sections
