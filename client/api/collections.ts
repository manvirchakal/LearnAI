import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { Collection } from "@/types/collection";

export const useCollections = () =>
  useQuery<Collection[]>({
    queryKey: ["collections"],
    queryFn: () => apiClient.get("/collections").then((r) => r.data),
  });

export const useCollection = (collectionId: string) =>
  useQuery<Collection>({
    queryKey: ["collections", collectionId],
    queryFn: () => apiClient.get(`/collections/${collectionId}`).then((r) => r.data),
    enabled: !!collectionId,
  });

export const useCreateCollection = () => {
  const qc = useQueryClient();
  return useMutation<Collection, Error, { name: string; materials: Record<string, unknown> }>({
    mutationFn: (payload) => apiClient.post("/collections", payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });
};

export const useUpdateCollectionMaterials = (collectionId: string) => {
  const qc = useQueryClient();
  return useMutation<Collection, Error, Record<string, unknown>>({
    mutationFn: (materials) =>
      apiClient.put(`/collections/${collectionId}/materials`, materials).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections", collectionId] }),
  });
};
