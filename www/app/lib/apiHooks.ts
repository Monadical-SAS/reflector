"use client";

import { $api } from "./apiClient";
import { useError } from "../(errors)/errorContext";
import { QueryClient, useQueryClient } from "@tanstack/react-query";
import type { components } from "../reflector-api";
import { useAuth } from "./AuthProvider";
import { MeetingId } from "./types";
import { NonEmptyString } from "./utils";

/*
 * ref 095959E6-01CC-4CF0-B3A9-F65F12F046D3
 * XXX error types returned from the hooks are not always correct; declared types are ValidationError but real type could be string or any other
 * this is either a limitation or incorrect usage of Python json schema generator
 * or, limitation or incorrect usage of .d type generator from json schema
 * */

export const useAuthReady = () => {
  const auth = useAuth();

  return {
    isAuthenticated: auth.status === "authenticated",
    isLoading: auth.status === "loading",
  };
};

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
    },
  );
}

type SourceKind = components["schemas"]["SourceKind"];

export const TRANSCRIPT_SEARCH_URL = "/v1/transcripts/search" as const;

export const invalidateTranscriptLists = (queryClient: QueryClient) =>
  queryClient.invalidateQueries({
    queryKey: ["get", TRANSCRIPT_SEARCH_URL],
  });

export function useTranscriptsSearch(
  q: string = "",
  options: {
    limit?: number;
    offset?: number;
    room_id?: string;
    source_kind?: SourceKind;
  } = {},
) {
  return $api.useQuery(
    "get",
    TRANSCRIPT_SEARCH_URL,
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
      enabled: true,
    },
  );
}

export function useTranscriptDelete() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("delete", "/v1/transcripts/{transcript_id}", {
    onSuccess: () => {
      return queryClient.invalidateQueries({
        queryKey: ["get", TRANSCRIPT_SEARCH_URL],
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

export function useTranscriptGet(transcriptId: NonEmptyString | null) {
  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}",
    {
      params: {
        path: {
          transcript_id: transcriptId!,
        },
      },
    },
    {
      enabled: !!transcriptId,
    },
  );
}

export const invalidateTranscript = (
  queryClient: QueryClient,
  transcriptId: NonEmptyString,
) =>
  queryClient.invalidateQueries({
    queryKey: $api.queryOptions("get", "/v1/transcripts/{transcript_id}", {
      params: { path: { transcript_id: transcriptId } },
    }).queryKey,
  });

export function useRoomGet(roomId: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms/{room_id}",
    {
      params: {
        path: { room_id: roomId! },
      },
    },
    {
      enabled: !!roomId && isAuthenticated,
    },
  );
}

export function useRoomTestWebhook() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/rooms/{room_id}/webhook/test", {
    onError: (error) => {
      setError(error as Error, "There was an error testing the webhook");
    },
  });
}

export function useRoomCreate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("post", "/v1/rooms", {
    onSuccess: () => {
      return queryClient.invalidateQueries({
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
    onSuccess: async (room) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
        }),
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions("get", "/v1/rooms/{room_id}", {
            params: {
              path: {
                room_id: room.id,
              },
            },
          }).queryKey,
        }),
      ]);
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
      return queryClient.invalidateQueries({
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
    },
  );
}

export function useTranscriptUpdate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("patch", "/v1/transcripts/{transcript_id}", {
    onSuccess: (data, variables) => {
      return queryClient.invalidateQueries({
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
        return queryClient.invalidateQueries({
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

export function useTranscriptWaveform(transcriptId: NonEmptyString | null) {
  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/waveform",
    {
      params: {
        path: { transcript_id: transcriptId! },
      },
    },
    {
      enabled: !!transcriptId,
    },
  );
}

export const invalidateTranscriptWaveform = (
  queryClient: QueryClient,
  transcriptId: NonEmptyString,
) =>
  queryClient.invalidateQueries({
    queryKey: $api.queryOptions(
      "get",
      "/v1/transcripts/{transcript_id}/audio/waveform",
      {
        params: { path: { transcript_id: transcriptId } },
      },
    ).queryKey,
  });

export function useTranscriptMP3(transcriptId: NonEmptyString | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/audio/mp3",
    {
      params: {
        path: { transcript_id: transcriptId! },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
    },
  );
}

export function useTranscriptTopics(transcriptId: NonEmptyString | null) {
  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics",
    {
      params: {
        path: { transcript_id: transcriptId! },
      },
    },
    {
      enabled: !!transcriptId,
    },
  );
}

export const invalidateTranscriptTopics = (
  queryClient: QueryClient,
  transcriptId: NonEmptyString,
) =>
  queryClient.invalidateQueries({
    queryKey: $api.queryOptions(
      "get",
      "/v1/transcripts/{transcript_id}/topics",
      {
        params: { path: { transcript_id: transcriptId } },
      },
    ).queryKey,
  });

export function useTranscriptTopicsWithWords(
  transcriptId: NonEmptyString | null,
) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/with-words",
    {
      params: {
        path: { transcript_id: transcriptId! },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
    },
  );
}

export function useTranscriptTopicsWithWordsPerSpeaker(
  transcriptId: NonEmptyString | null,
  topicId: string | null,
) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker",
    {
      params: {
        path: {
          transcript_id: transcriptId!,
          topic_id: topicId!,
        },
      },
    },
    {
      enabled: !!transcriptId && !!topicId && isAuthenticated,
    },
  );
}

export function useTranscriptParticipants(transcriptId: NonEmptyString | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/transcripts/{transcript_id}/participants",
    {
      params: {
        path: { transcript_id: transcriptId! },
      },
    },
    {
      enabled: !!transcriptId && isAuthenticated,
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
        return queryClient.invalidateQueries({
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
        return queryClient.invalidateQueries({
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
        return queryClient.invalidateQueries({
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
        return Promise.all([
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
          }),
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
          }),
        ]);
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
        return Promise.all([
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
          }),
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
          }),
        ]);
      },
      onError: (error) => {
        setError(error as Error, "There was an error merging speakers");
      },
    },
  );
}

export function useMeetingStartRecording() {
  const { setError } = useError();

  return $api.useMutation(
    "post",
    "/v1/meetings/{meeting_id}/recordings/start",
    {
      onError: (error) => {
        setError(error as Error, "Failed to start recording");
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

export function useMeetingDeactivate() {
  const { setError } = useError();
  const queryClient = useQueryClient();

  return $api.useMutation("patch", `/v1/meetings/{meeting_id}/deactivate`, {
    onError: (error) => {
      setError(error as Error, "Failed to end meeting");
    },
    onSuccess: () => {
      return queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return key.some(
            (k) =>
              typeof k === "string" &&
              !!MEETING_LIST_PATH_PARTIALS.find((e) => k.includes(e)),
          );
        },
      });
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
      return queryClient.invalidateQueries({
        queryKey: ["get", TRANSCRIPT_SEARCH_URL],
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
    onSuccess: async (data, variables) => {
      const roomName = variables.params.path.room_name;
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions("get", "/v1/rooms").queryKey,
        }),
        queryClient.invalidateQueries({
          queryKey: $api.queryOptions(
            "get",
            "/v1/rooms/{room_name}/meetings/active" satisfies `/v1/rooms/{room_name}/${typeof MEETINGS_ACTIVE_PATH_PARTIAL}`,
            {
              params: {
                path: { room_name: roomName },
              },
            },
          ).queryKey,
        }),
      ]);
    },
    onError: (error) => {
      setError(error as Error, "There was an error creating the meeting");
    },
  });
}

// Calendar integration hooks
export function useRoomGetByName(roomName: string | null) {
  return $api.useQuery(
    "get",
    "/v1/rooms/name/{room_name}",
    {
      params: {
        path: { room_name: roomName! },
      },
    },
    {
      enabled: !!roomName,
    },
  );
}

export function useRoomUpcomingMeetings(roomName: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms/{room_name}/meetings/upcoming" satisfies `/v1/rooms/{room_name}/${typeof MEETINGS_UPCOMING_PATH_PARTIAL}`,
    {
      params: {
        path: { room_name: roomName! },
      },
    },
    {
      enabled: !!roomName && isAuthenticated,
    },
  );
}

const MEETINGS_PATH_PARTIAL = "meetings" as const;
const MEETINGS_ACTIVE_PATH_PARTIAL = `${MEETINGS_PATH_PARTIAL}/active` as const;
const MEETINGS_UPCOMING_PATH_PARTIAL =
  `${MEETINGS_PATH_PARTIAL}/upcoming` as const;
const MEETING_LIST_PATH_PARTIALS = [
  MEETINGS_ACTIVE_PATH_PARTIAL,
  MEETINGS_UPCOMING_PATH_PARTIAL,
];

export function useRoomActiveMeetings(roomName: string | null) {
  return $api.useQuery(
    "get",
    "/v1/rooms/{room_name}/meetings/active" satisfies `/v1/rooms/{room_name}/${typeof MEETINGS_ACTIVE_PATH_PARTIAL}`,
    {
      params: {
        path: { room_name: roomName! },
      },
    },
    {
      enabled: !!roomName,
    },
  );
}

export function useRoomGetMeeting(
  roomName: string | null,
  meetingId: MeetingId | null,
) {
  return $api.useQuery(
    "get",
    "/v1/rooms/{room_name}/meetings/{meeting_id}",
    {
      params: {
        path: {
          room_name: roomName!,
          meeting_id: meetingId!,
        },
      },
    },
    {
      enabled: !!roomName && !!meetingId,
    },
  );
}

export function useRoomJoinMeeting() {
  const { setError } = useError();

  return $api.useMutation(
    "post",
    "/v1/rooms/{room_name}/meetings/{meeting_id}/join",
    {
      onError: (error) => {
        setError(error as Error, "There was an error joining the meeting");
      },
    },
  );
}

export function useRoomIcsSync() {
  const { setError } = useError();

  return $api.useMutation("post", "/v1/rooms/{room_name}/ics/sync", {
    onError: (error) => {
      setError(error as Error, "There was an error syncing the calendar");
    },
  });
}

export function useRoomIcsStatus(roomName: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms/{room_name}/ics/status",
    {
      params: {
        path: { room_name: roomName! },
      },
    },
    {
      enabled: !!roomName && isAuthenticated,
    },
  );
}

export function useRoomCalendarEvents(roomName: string | null) {
  const { isAuthenticated } = useAuthReady();

  return $api.useQuery(
    "get",
    "/v1/rooms/{room_name}/meetings",
    {
      params: {
        path: { room_name: roomName! },
      },
    },
    {
      enabled: !!roomName && isAuthenticated,
    },
  );
}
// End of Calendar integration hooks
