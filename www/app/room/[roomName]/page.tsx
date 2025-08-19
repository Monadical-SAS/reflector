"use client";

import { useEffect, useState } from "react";
import { Box, Spinner, VStack, Text } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import useApi from "../../lib/useApi";
import useSessionStatus from "../../lib/useSessionStatus";
import MeetingSelection from "../../[roomName]/MeetingSelection";
import { Meeting, Room } from "../../api";

interface RoomPageProps {
  params: {
    roomName: string;
  };
}

export default function RoomPage({ params }: RoomPageProps) {
  const { roomName } = params;
  const router = useRouter();
  const api = useApi();
  const { data: session } = useSessionStatus();

  const [room, setRoom] = useState<Room | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingMeetings, setCheckingMeetings] = useState(false);

  const isOwner = session?.user?.id === room?.user_id;

  useEffect(() => {
    if (!api) return;

    const fetchRoom = async () => {
      try {
        // Get room details
        const roomData = await api.v1RoomsRetrieve({ roomName });
        setRoom(roomData);

        // Check if we should show meeting selection
        if (roomData.ics_enabled) {
          setCheckingMeetings(true);

          // Check for active meetings
          const activeMeetings = await api.v1RoomsListActiveMeetings({
            roomName,
          });

          // Check for upcoming meetings
          const upcomingEvents = await api.v1RoomsListUpcomingMeetings({
            roomName,
            minutesAhead: 30,
          });

          // If there's only one active meeting and no upcoming, auto-join
          if (activeMeetings.length === 1 && upcomingEvents.length === 0) {
            handleMeetingSelect(activeMeetings[0]);
          } else if (
            activeMeetings.length === 0 &&
            upcomingEvents.length === 0
          ) {
            // No meetings, create unscheduled
            handleCreateUnscheduled();
          }
          // Otherwise, show selection UI (handled by render)
        } else {
          // ICS not enabled, use traditional flow
          handleCreateUnscheduled();
        }
      } catch (err) {
        console.error("Failed to fetch room:", err);
        // Room not found or error
        router.push("/rooms");
      } finally {
        setLoading(false);
        setCheckingMeetings(false);
      }
    };

    fetchRoom();
  }, [api, roomName]);

  const handleMeetingSelect = (meeting: Meeting) => {
    // Navigate to the classic room page with the meeting
    // Store meeting in session storage for the classic page to use
    sessionStorage.setItem(`meeting_${roomName}`, JSON.stringify(meeting));
    router.push(`/${roomName}`);
  };

  const handleCreateUnscheduled = async () => {
    if (!api) return;

    try {
      // Create a new unscheduled meeting
      const meeting = await api.v1RoomsCreateMeeting({ roomName });
      handleMeetingSelect(meeting);
    } catch (err) {
      console.error("Failed to create meeting:", err);
    }
  };

  if (loading || checkingMeetings) {
    return (
      <Box
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        bg="gray.50"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text>{loading ? "Loading room..." : "Checking meetings..."}</Text>
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
