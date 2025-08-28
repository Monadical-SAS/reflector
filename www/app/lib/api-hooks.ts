"use client";

import { $api } from "./apiClient";
import { useError } from "../(errors)/errorContext";
import { useQueryClient } from "@tanstack/react-query";
import type { paths } from "../reflector-api";

// Rooms hooks
export function useRoomsList(page: number = 1) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/rooms",
    {
      params: {
        query: { page },
      },
    },
    {
      onError: (error) => {
        setError(error as Error, "There was an error fetching the rooms");
      },
    },
  );
}

// Transcripts hooks
export function useTranscriptsSearch(
  q: string = "",
  options: {
    limit?: number;
    offset?: number;
    room_id?: string;
    source_kind?: string;
  } = {},
) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/search",
    {
      params: {
        query: {
          q,
          limit: options.limit,
          offset: options.offset,
          room_id: options.room_id,
          source_kind: options.source_kind as any,
        },
      },
    },
    {
      onError: (error) => {
        setError(error as Error, "There was an error searching transcripts");
      },
      keepPreviousData: true, // For smooth pagination
    },
  );
}

export function useTranscriptDelete() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("delete", "/v1/transcripts/{transcript_id}", {
    onSuccess: () => {
      // Invalidate transcripts queries to refetch
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/transcripts/search").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error deleting the transcript");
    },
  });
}

export function useTranscriptProcess() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/transcripts/{transcript_id}/process", {
    onError: (error) => {
      setError(error as Error, "There was an error processing the transcript");
    },
  });
}

export function useTranscriptGet(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}",
    {
      params: {
        path: {
          transcript_id: transcriptId || "",
        },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(error as Error, "There was an error loading the transcript");
      },
    },
  );
}
