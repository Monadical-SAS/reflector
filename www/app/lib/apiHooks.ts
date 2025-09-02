"use client";

import { $api } from "./apiClient";
import { useError } from "../(errors)/errorContext";
import { useQueryClient } from "@tanstack/react-query";
import type { components, paths } from "../reflector-api";
import useAuthReady from "./useAuthReady";

// FIXME: React Query caching issues with cross-tab synchronization
//
// The default React Query behavior caches data indefinitely until invalidated,
// which should work well in theory. However, we're experiencing two problems:
//
// 1. Navigation between pages doesn't refresh data as expected by users
// 2. Query invalidation doesn't work properly across browser tabs - changes
//    made in one tab (like updating room settings or deleting transcripts)
//    aren't reflected when navigating in another tab without a full page refresh
//
// As a temporary workaround, we're setting a short staleTime to force data
// reloading, similar to our previous implementation. This should be revisited
// once we can resolve the underlying invalidation and cross-tab sync issues.
// 500ms is arbitrary.
const STALE_TIME = 500;

export function useRoomsList(page: number = 1) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms",
    {
      params: {
        query: { page },
      },
    },
    {
      enabled: isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

type SourceKind = components["schemas"]["SourceKind"];

export function useTranscriptsSearch(
  q: string = "",
  options: {
    limit?: number;
    offset?: number;
    room_id?: string;
    source_kind?: SourceKind;
  } = {},
) {
  const { isAuthenticated } = useAuthReady();

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
          source_kind: options.source_kind,
        },
      },
    },
    {
      enabled: isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptDelete() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("delete", "/v1/transcripts/{transcript_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["get", "/v1/transcripts/search"],
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
  const { isAuthenticated } = useAuthReady();

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
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

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

export function useZulipStreams() {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/zulip/streams",
    {},
    {
      enabled: isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useZulipTopics(streamId: number | null) {
  const { isAuthenticated } = useAuthReady();
  const enabled = !!streamId && isAuthenticated;
  return $api.useQuery(
    "get",
    "/v1/zulip/streams/{stream_id}/topics",
    {
      params: {
        path: {
          stream_id: enabled ? streamId : 0,
        },
      },
    },
    {
      enabled,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptUpdate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("patch", "/v1/transcripts/{transcript_id}", {
    onSuccess: (data, variables) => {
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

export function useTranscriptWaveform(transcriptId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/waveform",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptMP3(transcriptId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/mp3",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptTopics(transcriptId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptTopicsWithWords(transcriptId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/with-words",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptTopicsWithWordsPerSpeaker(
  transcriptId: string | null,
  topicId: string | null,
) {
  const { isAuthenticated } = useAuthReady();

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
      enabled: !!transcriptId && !!topicId && isAuthenticated,
      staleTime: STALE_TIME,
    },
  );
}

export function useTranscriptParticipants(transcriptId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/participants",
    {
      params: {
        path: { transcript_id: transcriptId || "" },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
      staleTime: STALE_TIME,
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

export function useMeetingAudioConsent() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/meetings/{meeting_id}/consent", {
    onError: (error) => {
      setError(error as Error, "There was an error recording consent");
    },
  });
}

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

export function useTranscriptCreate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/transcripts", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["get", "/v1/transcripts/search"],
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the transcript");
    },
  });
}

export function useRoomsCreateMeeting() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/rooms/{room_name}/meeting", {
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
      });
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the meeting");
    },
  });
}
