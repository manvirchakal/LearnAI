import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import { collectionUnit, studyKey } from "./study";
import type { Collection, CollectionMaterials } from "@/types/collection";

export const collectionKeys = {
  all: ["collections"] as const,
  detail: (collectionId: string) => ["collections", collectionId] as const,
};

/** User-created collections, newest first (per-upload collections are left out). */
export const useCollections = () =>
  useQuery<Collection[]>({
    queryKey: collectionKeys.all,
    queryFn: () => apiClient.get("/collections").then((r) => r.data),
  });

export const useCollection = (collectionId: string) =>
  useQuery<Collection>({
    queryKey: collectionKeys.detail(collectionId),
    queryFn: () => apiClient.get(`/collections/${collectionId}`).then((r) => r.data),
    enabled: !!collectionId,
  });

export const useCreateCollection = () => {
  const qc = useQueryClient();
  return useMutation<Collection, Error, { name: string; materials: CollectionMaterials }>({
    mutationFn: (payload) => apiClient.post("/collections", payload).then((r) => r.data),
    onSuccess: (col) => {
      qc.setQueryData(collectionKeys.detail(col.collection_id), col);
      qc.invalidateQueries({ queryKey: collectionKeys.all, exact: true });
    },
  });
};

export const useRenameCollection = (collectionId: string) => {
  const qc = useQueryClient();
  return useMutation<Collection, Error, string>({
    mutationFn: (name) => apiClient.patch(`/collections/${collectionId}`, { name }).then((r) => r.data),
    onSuccess: (col) => {
      qc.setQueryData(collectionKeys.detail(collectionId), col);
      qc.invalidateQueries({ queryKey: collectionKeys.all, exact: true });
    },
  });
};

/** Replace a collection's materials. The server drops its generated study materials. */
export const useUpdateCollectionMaterials = () => {
  const qc = useQueryClient();
  return useMutation<Collection, Error, { collectionId: string; materials: CollectionMaterials }>({
    mutationFn: ({ collectionId, materials }) =>
      apiClient.put(`/collections/${collectionId}/materials`, materials).then((r) => r.data),
    onSuccess: (col) => {
      qc.setQueryData(collectionKeys.detail(col.collection_id), col);
      qc.setQueryData(studyKey(collectionUnit(col.collection_id)), null);
      qc.invalidateQueries({ queryKey: collectionKeys.all, exact: true });
    },
  });
};

export const useDeleteCollection = () => {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (collectionId) => apiClient.delete(`/collections/${collectionId}`).then(() => undefined),
    // The detail page is still mounted here; removing its queries would refetch them (404).
    // They are dropped when unused, after the page navigates away.
    onSuccess: () => qc.invalidateQueries({ queryKey: collectionKeys.all, exact: true }),
  });
};
