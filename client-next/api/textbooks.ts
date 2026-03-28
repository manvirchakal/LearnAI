import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type { BookItem, BookStructure } from "@/types/textbook";

export const useUserTextbooks = () =>
  useQuery<BookItem[]>({
    queryKey: ["textbooks"],
    queryFn: () => apiClient.get("/user-textbooks").then((r) => r.data),
  });

export const useUserBooks = () =>
  useQuery<BookItem[]>({
    queryKey: ["books"],
    queryFn: () => apiClient.get("/user-books").then((r) => r.data),
  });

export const useTextbookStructure = (userId: string, fileId: string, filename: string) =>
  useQuery<BookStructure>({
    queryKey: ["textbook-structure", userId, fileId, filename],
    queryFn: () =>
      apiClient.get(`/textbook-structure/${userId}/${fileId}/${filename}`).then((r) => r.data),
    enabled: !!userId && !!fileId && !!filename,
  });

export const useUploadPDF = () =>
  useMutation<unknown, Error, FormData>({
    mutationFn: (formData) =>
      apiClient
        .post("/upload-pdf", formData, { headers: { "Content-Type": "multipart/form-data" } })
        .then((r) => r.data),
  });

export const useProcessSection = () =>
  useMutation<{ extracted_text: string }, Error, FormData>({
    mutationFn: (formData) =>
      apiClient
        .post("/process-pdf-section", formData, { headers: { "Content-Type": "multipart/form-data" } })
        .then((r) => r.data),
  });
