"use client";

import {
  Box,
  VStack,
  HStack,
  Text,
  Spinner,
  Button,
  Icon,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FaClock, FaArrowLeft } from "react-icons/fa";
import type { components } from "../../../reflector-api";
import {
  useRoomUpcomingMeetings,
  useRoomActiveMeetings,
  useRoomJoinMeeting,
} from "../../../lib/apiHooks";

type CalendarEventResponse = components["schemas"]["CalendarEventResponse"];

interface WaitingPageProps {
  params: {
    roomName: string;
  };
}

export default function WaitingPage({ params }: WaitingPageProps) {
  const { roomName } = params;
  const router = useRouter();
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");

  const [event, setEvent] = useState<CalendarEventResponse | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [checkingMeeting, setCheckingMeeting] = useState(false);

  // Use React Query hooks
  const upcomingMeetingsQuery = useRoomUpcomingMeetings(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();
  const loading = upcomingMeetingsQuery.isLoading;

  useEffect(() => {
    if (!eventId || !upcomingMeetingsQuery.data) return;

    const targetEvent = upcomingMeetingsQuery.data.find(
      (e) => e.id === eventId,
    );
    if (targetEvent) {
      setEvent(targetEvent);
    } else if (!upcomingMeetingsQuery.isLoading) {
      // Event not found or already started
      router.push(`/room/${roomName}`);
    }
  }, [
    eventId,
    upcomingMeetingsQuery.data,
    upcomingMeetingsQuery.isLoading,
    router,
    roomName,
  ]);

  // Handle query errors
  useEffect(() => {
    if (upcomingMeetingsQuery.error) {
      console.error("Failed to fetch event:", upcomingMeetingsQuery.error);
      router.push(`/room/${roomName}`);
    }
  }, [upcomingMeetingsQuery.error, router, roomName]);

  useEffect(() => {
    if (!event) return;

    const updateCountdown = () => {
      const now = new Date();
      const start = new Date(event.start_time);
      const diff = Math.max(0, start.getTime() - now.getTime());

      setTimeRemaining(diff);

      // Check if meeting has started
      if (diff <= 0) {
        checkForActiveMeeting();
      }
    };

    const checkForActiveMeeting = async () => {
      if (checkingMeeting) return;

      setCheckingMeeting(true);
      try {
        // Refetch active meetings to get latest data
        const result = await activeMeetingsQuery.refetch();
        if (!result.data) return;

        // Find meeting for this calendar event
        const calendarMeeting = result.data.find(
          (m) => m.calendar_event_id === eventId,
        );

        if (calendarMeeting) {
          // Meeting is now active, join it
          const meeting = await joinMeetingMutation.mutateAsync({
            params: {
              path: { room_name: roomName, meeting_id: calendarMeeting.id },
            },
          });

          // Navigate to the meeting room
          router.push(`/${roomName}?meetingId=${meeting.id}`);
        }
      } catch (err) {
        console.error("Failed to check for active meeting:", err);
      } finally {
        setCheckingMeeting(false);
      }
    };

    // Update countdown every second
    const interval = setInterval(updateCountdown, 1000);

    // Check for meeting every 10 seconds when close to start time
    let checkInterval: NodeJS.Timeout | null = null;
    if (timeRemaining < 60000) {
      // Less than 1 minute
      checkInterval = setInterval(checkForActiveMeeting, 10000);
    }

    updateCountdown(); // Initial update

    return () => {
      clearInterval(interval);
      if (checkInterval) clearInterval(checkInterval);
    };
  }, [
    event,
    eventId,
    roomName,
    checkingMeeting,
    activeMeetingsQuery,
    joinMeetingMutation,
  ]);

  const formatTime = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds
        .toString()
        .padStart(2, "0")}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  const getProgressValue = () => {
    if (!event) return 0;

    const now = new Date();
    const created = new Date(event.created_at);
    const start = new Date(event.start_time);
    const totalTime = start.getTime() - created.getTime();
    const elapsed = now.getTime() - created.getTime();

    return Math.min(100, (elapsed / totalTime) * 100);
  };

  if (loading) {
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
          <Text>Loading meeting details...</Text>
        </VStack>
      </Box>
    );
  }

  if (!event) {
    return (
      <Box
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        bg="gray.50"
      >
        <VStack gap={4}>
          <Text fontSize="lg">Meeting not found</Text>
          <Button onClick={() => router.push(`/room/${roomName}`)}>
            <FaArrowLeft />
            Back to Room
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg="gray.50"
    >
      <Box
        maxW="lg"
        width="100%"
        mx={4}
        bg="white"
        borderRadius="lg"
        boxShadow="md"
        p={6}
      >
        <VStack gap={6}>
          <Icon as={FaClock} boxSize={16} color="blue.500" />

          <VStack gap={2}>
            <Text fontSize="2xl" fontWeight="bold">
              {event.title || "Scheduled Meeting"}
            </Text>
            <Text color="gray.600" textAlign="center">
              The meeting will start automatically when it's time
            </Text>
          </VStack>

          <Box width="100%">
            <Text
              fontSize="4xl"
              fontWeight="bold"
              textAlign="center"
              color="blue.600"
            >
              {formatTime(timeRemaining)}
            </Text>
            <Box
              width="100%"
              height="8px"
              bg="gray.200"
              borderRadius="full"
              mt={4}
              position="relative"
              overflow="hidden"
            >
              <Box
                width={`${getProgressValue()}%`}
                height="100%"
                bg="blue.500"
                borderRadius="full"
                transition="width 0.3s ease"
              />
            </Box>
          </Box>

          {event.description && (
            <Box width="100%" p={4} bg="gray.100" borderRadius="md">
              <Text fontSize="sm" fontWeight="semibold" mb={1}>
                Meeting Description
              </Text>
              <Text fontSize="sm" color="gray.700">
                {event.description}
              </Text>
            </Box>
          )}

          <VStack gap={3} width="100%">
            <Text fontSize="sm" color="gray.500">
              Scheduled for {new Date(event.start_time).toLocaleString()}
            </Text>

            {checkingMeeting && (
              <HStack gap={2}>
                <Spinner size="sm" color="blue.500" />
                <Text fontSize="sm" color="blue.600">
                  Checking if meeting has started...
                </Text>
              </HStack>
            )}
          </VStack>

          <Button
            variant="outline"
            onClick={() => router.push(`/room/${roomName}`)}
            width="100%"
          >
            <FaArrowLeft />
            Back to Meeting Selection
          </Button>
        </VStack>
      </Box>
    </Box>
  );
}
