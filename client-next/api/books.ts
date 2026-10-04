import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient, { API_BASE } from "./client";
import type { BookDetail, BookSummary, UploadBookInput } from "@/types/book";

export const bookKeys = {
  all: ["books"] as const,
  detail: (fileId: string) => ["books", fileId] as const,
};

export const useBooks = () =>
  useQuery<BookSummary[]>({
    queryKey: bookKeys.all,
    queryFn: () => apiClient.get("/books").then((r) => r.data),
  });

export const useBook = (fileId: string) =>
  useQuery<BookDetail>({
    queryKey: bookKeys.detail(fileId),
    queryFn: () => apiClient.get(`/books/${fileId}`).then((r) => r.data),
    enabled: !!fileId,
    staleTime: Infinity, // structure never changes after upload
  });

export const useUploadBook = () => {
  const qc = useQueryClient();
  return useMutation<BookDetail, Error, UploadBookInput>({
    mutationFn: ({ file, documentType = "textbook", tocPages }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("document_type", documentType);
      if (tocPages) form.append("toc_pages", tocPages);
      return apiClient.post("/books", form).then((r) => r.data);
    },
    onSuccess: (book) => {
      qc.setQueryData(bookKeys.detail(book.file_id), book);
      qc.invalidateQueries({ queryKey: bookKeys.all, exact: true });
    },
  });
};

export const useDeleteBook = () => {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (fileId) => apiClient.delete(`/books/${fileId}`).then(() => undefined),
    onSuccess: (_, fileId) => {
      qc.removeQueries({ queryKey: bookKeys.detail(fileId) });
      qc.invalidateQueries({ queryKey: bookKeys.all, exact: true });
    },
  });
};

export const sectionPdfUrl = (fileId: string, sectionId: string) =>
  `${API_BASE}/books/${fileId}/sections/${sectionId}/pdf`;
