"use client";

import { roomMeetingUrl } from "../../lib/routes";
import { useCallback, useEffect, useState, use } from "react";
import { Box, Text, Spinner } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import {
  useRoomGetByName,
  useRoomsCreateMeeting,
  useRoomGetMeeting,
} from "../../lib/apiHooks";
import type { components } from "../../reflector-api";
import MeetingSelection from "../MeetingSelection";
import useRoomDefaultMeeting from "../useRoomDefaultMeeting";
import WherebyRoom from "./WherebyRoom";
import DailyRoom from "./DailyRoom";
import { useAuth } from "../../lib/AuthProvider";
import { useError } from "../../(errors)/errorContext";
import { parseNonEmptyString } from "../../lib/utils";
import { printApiError } from "../../api/_error";
import { assertMeetingId } from "../../lib/types";

type Meeting = components["schemas"]["Meeting"];

export type RoomDetails = {
  params: Promise<{
    roomName: string;
    meetingId?: string;
  }>;
};

function LoadingSpinner() {
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      height="100vh"
      bg="gray.50"
      p={4}
    >
      <Spinner color="blue.500" size="xl" />
    </Box>
  );
}

export default function RoomContainer(details: RoomDetails) {
  const params = use(details.params);
  const roomName = parseNonEmptyString(
    params.roomName,
    true,
    "panic! params.roomName is required",
  );
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";
  const { setError } = useError();

  const roomQuery = useRoomGetByName(roomName);
  const createMeetingMutation = useRoomsCreateMeeting();

  const room = roomQuery.data;

  const pageMeetingId = params.meetingId;

  const defaultMeeting = useRoomDefaultMeeting(
    room && !room.ics_enabled && !pageMeetingId ? roomName : null,
  );

  const explicitMeeting = useRoomGetMeeting(
    roomName,
    pageMeetingId ? assertMeetingId(pageMeetingId) : null,
  );

  const meeting = explicitMeeting.data || defaultMeeting.response;

  const isLoading =
    status === "loading" ||
    roomQuery.isLoading ||
    defaultMeeting?.loading ||
    explicitMeeting.isLoading ||
    createMeetingMutation.isPending;

  const errors = [
    explicitMeeting.error,
    defaultMeeting.error,
    roomQuery.error,
    createMeetingMutation.error,
  ].filter(Boolean);

  const isOwner =
    isAuthenticated && room ? auth.user?.id === room.user_id : false;

  const handleMeetingSelect = (selectedMeeting: Meeting) => {
    router.push(
      roomMeetingUrl(
        roomName,
        parseNonEmptyString(
          selectedMeeting.id,
          true,
          "panic! selectedMeeting.id is required",
        ),
      ),
    );
  };

  const handleCreateUnscheduled = async () => {
    try {
      const newMeeting = await createMeetingMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
        body: {
          allow_duplicated: room ? room.ics_enabled : false,
        },
      });
      handleMeetingSelect(newMeeting);
    } catch (err) {
      console.error("Failed to create meeting:", err);
    }
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!room) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        <Text fontSize="lg">Room not found</Text>
      </Box>
    );
  }

  if (room.ics_enabled && !params.meetingId) {
    return (
      <MeetingSelection
        roomName={roomName}
        isOwner={isOwner}
        isSharedRoom={room?.is_shared || false}
        authLoading={["loading", "refreshing"].includes(auth.status)}
        onMeetingSelect={handleMeetingSelect}
        onCreateUnscheduled={handleCreateUnscheduled}
        isCreatingMeeting={createMeetingMutation.isPending}
      />
    );
  }

  if (errors.length > 0) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        {errors.map((error, i) => (
          <Text key={i} fontSize="lg">
            {printApiError(error)}
          </Text>
        ))}
      </Box>
    );
  }

  if (!meeting) {
    return <LoadingSpinner />;
  }

  const platform = meeting.platform;

  if (!platform) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        <Text fontSize="lg">Meeting platform not configured</Text>
      </Box>
    );
  }

  switch (platform) {
    case "daily":
      return <DailyRoom meeting={meeting} room={room} />;
    case "whereby":
      return <WherebyRoom meeting={meeting} room={room} />;
    default: {
      const _exhaustive: never = platform;
      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          height="100vh"
          bg="gray.50"
          p={4}
        >
          <Text fontSize="lg">Unknown platform: {platform}</Text>
        </Box>
      );
    }
  }
}
