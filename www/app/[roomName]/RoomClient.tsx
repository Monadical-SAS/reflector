"use client";

import { useEffect } from "react";
import { Box, Spinner, Text } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import {
  useRoomGetByName,
  useRoomActiveMeetings,
  useRoomUpcomingMeetings,
  useRoomsCreateMeeting,
} from "../lib/apiHooks";
import type { components } from "../reflector-api";
import MeetingSelection from "./MeetingSelection";
import { useAuth } from "../lib/AuthProvider";
import useRoomMeeting from "./useRoomMeeting";
import dynamic from "next/dynamic";

const WherebyEmbed = dynamic(() => import("../lib/WherebyWebinarEmbed"), {
  ssr: false,
});

type Meeting = components["schemas"]["Meeting"];

interface RoomClientProps {
  params: {
    roomName: string;
  };
}

export default function RoomClient({ params }: RoomClientProps) {
  const roomName = params.roomName;
  const router = useRouter();
  const auth = useAuth();

  // Fetch room details using React Query
  const roomQuery = useRoomGetByName(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const upcomingMeetingsQuery = useRoomUpcomingMeetings(roomName);
  const createMeetingMutation = useRoomsCreateMeeting();

  const room = roomQuery.data;
  const activeMeetings = activeMeetingsQuery.data || [];
  const upcomingMeetings = upcomingMeetingsQuery.data || [];

  // For non-ICS rooms, create a meeting and get Whereby URL
  const roomMeeting = useRoomMeeting(
    room && !room.ics_enabled ? roomName : null,
  );
  const roomUrl =
    roomMeeting?.response?.host_room_url || roomMeeting?.response?.room_url;

  const isLoading = auth.status === "loading" || roomQuery.isLoading;

  const isOwner =
    auth.status === "authenticated" && room
      ? auth.user?.id === room.user_id
      : false;

  const handleMeetingSelect = (selectedMeeting: Meeting) => {
    // Navigate to specific meeting using path segment
    router.push(`/${roomName}/${selectedMeeting.id}`);
  };

  const handleCreateUnscheduled = async () => {
    try {
      // Create a new unscheduled meeting
      const newMeeting = await createMeetingMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
      });
      handleMeetingSelect(newMeeting);
    } catch (err) {
      console.error("Failed to create meeting:", err);
    }
  };

  // Handle room not found
  useEffect(() => {
    if (roomQuery.isError) {
      router.push("/");
    }
  }, [roomQuery.isError, router]);

  if (isLoading) {
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

  // For ICS-enabled rooms, show meeting selection
  if (room.ics_enabled) {
    return (
      <MeetingSelection
        roomName={roomName}
        isOwner={isOwner}
        isSharedRoom={room?.is_shared || false}
        authLoading={["loading", "refreshing"].includes(auth.status)}
        onMeetingSelect={handleMeetingSelect}
        onCreateUnscheduled={handleCreateUnscheduled}
      />
    );
  }

  // For non-ICS rooms, show Whereby embed directly
  if (roomUrl) {
    return <WherebyEmbed roomUrl={roomUrl} />;
  }

  // Loading state for non-ICS rooms while creating meeting
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
