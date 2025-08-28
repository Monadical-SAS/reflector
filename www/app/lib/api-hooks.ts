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

// Rooms mutations
export function useRoomCreate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/rooms", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the room");
    },
  });
}

export function useRoomUpdate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("patch", "/v1/rooms/{room_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error updating the room");
    },
  });
}

export function useRoomDelete() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("delete", "/v1/rooms/{room_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error deleting the room");
    },
  });
}

// Zulip hooks
export function useZulipStreams() {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/zulip/get-streams",
    {},
    {
      onError: (error) => {
        setError(error as Error, "There was an error fetching Zulip streams");
      },
    },
  );
}

export function useZulipTopics(streamId: number | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/zulip/get-topics",
    {
      params: {
        query: { stream_id: streamId || 0 },
      },
    },
    {
      enabled: !!streamId,
      onError: (error) => {
        setError(error as Error, "There was an error fetching Zulip topics");
      },
    },
  );
}

// Transcript mutations
export function useTranscriptUpdate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("patch", "/v1/transcripts/{transcript_id}", {
    onSuccess: (data, variables) => {
      // Invalidate and refetch transcript data
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/transcripts/{transcript_id}", {
          params: {
            path: { transcript_id: variables.params.path.transcript_id },
          },
        }).queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error updating the transcript");
    },
  });
}

export function useTranscriptPostToZulip() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/transcripts/{transcript_id}/zulip", {
    onError: (error) => {
      setError(error as Error, "There was an error posting to Zulip");
    },
  });
}

export function useTranscriptUploadAudio() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/record/upload",
    {
      onSuccess: (data, variables) => {
        // Invalidate transcript to refresh status
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
      },
      onError: (error) => {
        setError(error as Error, "There was an error uploading the audio file");
      },
    },
  );
}

// Transcript queries
export function useTranscriptWaveform(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/waveform",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(error as Error, "There was an error fetching the waveform");
      },
    },
  );
}

export function useTranscriptMP3(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/mp3",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(error as Error, "There was an error fetching the MP3");
      },
    },
  );
}

export function useTranscriptTopics(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(error as Error, "There was an error fetching topics");
      },
    },
  );
}

export function useTranscriptTopicsWithWords(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/with-words",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(
          error as Error,
          "There was an error fetching topics with words",
        );
      },
    },
  );
}

// Participant operations
export function useTranscriptParticipants(transcriptId: string | null) {
  const { setError } = useError();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/participants",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId,
      onError: (error) => {
        setError(error as Error, "There was an error fetching participants");
      },
    },
  );
}

export function useTranscriptParticipantUpdate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "patch",
    "/v1/transcripts/{transcript_id}/participants/{participant_id}",
    {
      onSuccess: (data, variables) => {
        // Invalidate participants list
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}/participants",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
      },
      onError: (error) => {
        setError(error as Error, "There was an error updating the participant");
      },
    },
  );
}

export function useTranscriptSpeakerAssign() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/speaker/assign",
    {
      onSuccess: (data, variables) => {
        // Invalidate transcript and participants
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}/participants",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
      },
      onError: (error) => {
        setError(error as Error, "There was an error assigning the speaker");
      },
    },
  );
}

export function useTranscriptSpeakerMerge() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/speaker/merge",
    {
      onSuccess: (data, variables) => {
        // Invalidate transcript and participants
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/transcripts/{transcript_id}/participants",
            {
              params: {
                path: { transcript_id: variables.params.path.transcript_id },
              },
            },
          ).queryKey,
        });
      },
      onError: (error) => {
        setError(error as Error, "There was an error merging speakers");
      },
    },
  );
}

// Meeting operations
export function useMeetingAudioConsent() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/meetings/{meeting_id}/consent", {
    onError: (error) => {
      setError(error as Error, "There was an error recording consent");
    },
  });
}

// WebRTC operations
export function useTranscriptWebRTC() {
  const { setError } = useError();

  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/record/webrtc",
    {
      onError: (error) => {
        setError(error as Error, "There was an error with WebRTC connection");
      },
    },
  );
}

// Transcript creation
export function useTranscriptCreate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/transcripts", {
    onSuccess: () => {
      // Invalidate transcripts list
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/transcripts/search").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the transcript");
    },
  });
}
