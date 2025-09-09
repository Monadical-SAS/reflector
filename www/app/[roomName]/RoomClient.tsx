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

  const isOwner =
    auth.status === "authenticated" ? auth.user?.id === room?.user_id : false;

  const isLoading = auth.status === "loading" || roomQuery.isLoading;

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

  // For non-ICS rooms, automatically create and join meeting
  useEffect(() => {
    if (!room || isLoading || room.ics_enabled) return;

    // Non-ICS room: create meeting automatically
    handleCreateUnscheduled();
  }, [room, isLoading]);

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

  // For ICS-enabled rooms, ALWAYS show meeting selection (no auto-redirect)
  if (room.ics_enabled) {
    return (
      <MeetingSelection
        roomName={roomName}
        isOwner={isOwner}
        isSharedRoom={room?.is_shared || false}
        onMeetingSelect={handleMeetingSelect}
        onCreateUnscheduled={handleCreateUnscheduled}
      />
    );
  }

  // Non-ICS rooms will auto-redirect via useEffect above
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
