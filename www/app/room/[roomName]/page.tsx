"use client";

import { useEffect, useState } from "react";
import { Box, Spinner, VStack, Text } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import {
  useRoomGetByName,
  useRoomUpcomingMeetings,
  useRoomActiveMeetings,
  useRoomsCreateMeeting,
} from "../../lib/apiHooks";
import MeetingSelection from "../../[roomName]/MeetingSelection";

type Meeting = components["schemas"]["Meeting"];
type Room = components["schemas"]["Room"];

interface RoomPageProps {
  params: {
    roomName: string;
  };
}

export default function RoomPage({ params }: RoomPageProps) {
  const { roomName } = params;
  const router = useRouter();
  const auth = useAuth();

  // React Query hooks
  const roomQuery = useRoomGetByName(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const upcomingMeetingsQuery = useRoomUpcomingMeetings(roomName);
  const createMeetingMutation = useRoomsCreateMeeting();

  const room = roomQuery.data;
  const activeMeetings = activeMeetingsQuery.data || [];
  const upcomingMeetings = upcomingMeetingsQuery.data || [];

  const isLoading = roomQuery.isLoading;
  const isCheckingMeetings =
    (room?.ics_enabled &&
      (activeMeetingsQuery.isLoading || upcomingMeetingsQuery.isLoading)) ||
    createMeetingMutation.isPending;

  const isOwner =
    auth.status === "authenticated" && auth.user?.id === room?.user_id;

  const handleMeetingSelect = (meeting: Meeting) => {
    // Navigate to the classic room page with the meeting
    // Store meeting in session storage for the classic page to use
    sessionStorage.setItem(`meeting_${roomName}`, JSON.stringify(meeting));
    router.push(`/${roomName}`);
  };

  const handleCreateUnscheduled = async () => {
    try {
      // Create a new unscheduled meeting
      const meeting = await createMeetingMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
      });
      handleMeetingSelect(meeting);
    } catch (err) {
      console.error("Failed to create meeting:", err);
    }
  };

  // Auto-navigate logic based on query results
  useEffect(() => {
    if (!room || isLoading || isCheckingMeetings) return;

    if (room.ics_enabled) {
      // If there's only one active meeting and no upcoming, auto-join
      if (activeMeetings.length === 1 && upcomingMeetings.length === 0) {
        handleMeetingSelect(activeMeetings[0]);
      } else if (activeMeetings.length === 0 && upcomingMeetings.length === 0) {
        // No meetings, create unscheduled
        handleCreateUnscheduled();
      }
      // Otherwise, show selection UI (handled by render)
    } else {
      // ICS not enabled, use traditional flow
      handleCreateUnscheduled();
    }
  }, [room, activeMeetings, upcomingMeetings, isLoading, isCheckingMeetings]);

  // Handle room not found
  useEffect(() => {
    if (roomQuery.isError) {
      router.push("/rooms");
    }
  }, [roomQuery.isError, router]);

  if (isLoading || isCheckingMeetings) {
    return (
      <Box
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        bg="gray.50"
      >
        <VStack gap={4}>
          <Spinner size="xl" color="blue.500" />
          <Text>{isLoading ? "Loading room..." : "Checking meetings..."}</Text>
        </VStack>
      </Box>
    );
  }

  if (!room) {
    return (
      <Box
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        bg="gray.50"
      >
        <Text fontSize="lg">Room not found</Text>
      </Box>
    );
  }

  // Show meeting selection if ICS is enabled and we have multiple options
  if (room.ics_enabled) {
    return (
      <Box minH="100vh" bg="gray.50">
        <MeetingSelection
          roomName={roomName}
          isOwner={isOwner}
          onMeetingSelect={handleMeetingSelect}
          onCreateUnscheduled={handleCreateUnscheduled}
        />
      </Box>
    );
  }

  // Should not reach here - redirected above
  return null;
}
