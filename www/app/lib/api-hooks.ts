"use client";

import { $api } from "./apiClient";
import { useError } from "../(errors)/errorContext";
import { useQueryClient } from "@tanstack/react-query";
import type { paths } from "../reflector-api";
import useAuthReady from "./useAuthReady";

// Rooms hooks
export function useRoomsList(page: number = 1) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms",
    {
      params: {
        query: { page },
      },
    },
    {
      // Only fetch when authentication is fully ready (session + token)
      enabled: isAuthReady,
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
  const { isAuthReady } = useAuthReady();

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
      // Only fetch when authentication is fully ready (session + token)
      enabled: isAuthReady,
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
        queryKey: $api.queryOptions("get", "/v1/transcripts/search", {
          params: { query: { q: "" } },
        }).queryKey,
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
  const { isAuthReady } = useAuthReady();

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
      // Only fetch when authenticated and transcriptId is provided
      enabled: !!transcriptId && isAuthReady,
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

// Zulip hooks - NOTE: These endpoints are not in the OpenAPI spec yet
export function useZulipStreams() {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  // @ts-ignore - Zulip endpoint not in OpenAPI spec
  return $api.useQuery(
    "get",
    "/v1/zulip/streams" as any,
    {},
    {
      // Only fetch when authenticated
      enabled: isAuthReady,
    },
  );
}

export function useZulipTopics(streamId: number | null) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  // @ts-ignore - Zulip endpoint not in OpenAPI spec
  return $api.useQuery(
    "get",
    streamId ? (`/v1/zulip/streams/${streamId}/topics` as any) : null,
    {},
    {
      // Only fetch when authenticated and streamId is provided
      enabled: !!streamId && isAuthReady,
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

  // @ts-ignore - Zulip endpoint not in OpenAPI spec
  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/zulip" as any,
    {
      onError: (error) => {
        setError(error as Error, "There was an error posting to Zulip");
      },
    },
  );
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
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/waveform",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthReady,
    },
  );
}

export function useTranscriptMP3(transcriptId: string | null) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/mp3",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthReady,
    },
  );
}

export function useTranscriptTopics(transcriptId: string | null) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthReady,
    },
  );
}

export function useTranscriptTopicsWithWords(transcriptId: string | null) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/with-words",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthReady,
    },
  );
}

export function useTranscriptTopicsWithWordsPerSpeaker(
  transcriptId: string | null,
  topicId: string | null,
) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker",
    {
      params: {
        path: {
          transcript_id: transcriptId || "",
          topic_id: topicId || "",
        },
      },
    },
    {
      enabled: !!transcriptId && !!topicId && isAuthReady,
    },
  );
}

// Participant operations
export function useTranscriptParticipants(transcriptId: string | null) {
  const { setError } = useError();
  const { isAuthReady } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/participants",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthReady,
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

export function useTranscriptParticipantCreate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "post",
    "/v1/transcripts/{transcript_id}/participants",
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
        setError(error as Error, "There was an error creating the participant");
      },
    },
  );
}

export function useTranscriptParticipantDelete() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "delete",
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
        setError(error as Error, "There was an error deleting the participant");
      },
    },
  );
}

export function useTranscriptSpeakerAssign() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation(
    "patch",
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
    "patch",
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
        queryKey: $api.queryOptions("get", "/v1/transcripts/search", {
          params: { query: { q: "" } },
        }).queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the transcript");
    },
  });
}

// Rooms meeting operations
export function useRoomsCreateMeeting() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/rooms/{room_name}/meeting", {
    onSuccess: () => {
      // Invalidate rooms list to refresh meeting data
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the meeting");
    },
  });
}
