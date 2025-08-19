"use client";

import {
  Box,
  VStack,
  HStack,
  Text,
  Spinner,
  Progress,
  Card,
  CardBody,
  Button,
  Icon,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FaClock, FaArrowLeft } from "react-icons/fa";
import useApi from "../../../lib/useApi";
import { CalendarEventResponse } from "../../../api";

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
  const [loading, setLoading] = useState(true);
  const [checkingMeeting, setCheckingMeeting] = useState(false);
  const api = useApi();

  useEffect(() => {
    if (!api || !eventId) return;

    const fetchEvent = async () => {
      try {
        const events = await api.v1RoomsListUpcomingMeetings({
          roomName,
          minutesAhead: 60,
        });

        const targetEvent = events.find((e) => e.id === eventId);
        if (targetEvent) {
          setEvent(targetEvent);
        } else {
          // Event not found or already started
          router.push(`/room/${roomName}`);
        }
      } catch (err) {
        console.error("Failed to fetch event:", err);
        router.push(`/room/${roomName}`);
      } finally {
        setLoading(false);
      }
    };

    fetchEvent();
  }, [api, eventId, roomName]);

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
      if (!api || checkingMeeting) return;

      setCheckingMeeting(true);
      try {
        // Check for active meetings
        const activeMeetings = await api.v1RoomsListActiveMeetings({
          roomName,
        });

        // Find meeting for this calendar event
        const calendarMeeting = activeMeetings.find(
          (m) => m.calendar_event_id === eventId,
        );

        if (calendarMeeting) {
          // Meeting is now active, join it
          const meeting = await api.v1RoomsJoinMeeting({
            roomName,
            meetingId: calendarMeeting.id,
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
  }, [event, api, eventId, roomName, checkingMeeting]);

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
        <VStack spacing={4}>
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
        <VStack spacing={4}>
          <Text fontSize="lg">Meeting not found</Text>
          <Button
            leftIcon={<FaArrowLeft />}
            onClick={() => router.push(`/room/${roomName}`)}
          >
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
      <Card maxW="lg" width="100%" mx={4}>
        <CardBody>
          <VStack spacing={6} py={4}>
            <Icon as={FaClock} boxSize={16} color="blue.500" />

            <VStack spacing={2}>
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
              <Progress
                value={getProgressValue()}
                colorScheme="blue"
                size="sm"
                mt={4}
                borderRadius="full"
              />
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

            <VStack spacing={3} width="100%">
              <Text fontSize="sm" color="gray.500">
                Scheduled for {new Date(event.start_time).toLocaleString()}
              </Text>

              {checkingMeeting && (
                <HStack spacing={2}>
                  <Spinner size="sm" color="blue.500" />
                  <Text fontSize="sm" color="blue.600">
                    Checking if meeting has started...
                  </Text>
                </HStack>
              )}
            </VStack>

            <Button
              variant="outline"
              leftIcon={<FaArrowLeft />}
              onClick={() => router.push(`/room/${roomName}`)}
              width="100%"
            >
              Back to Meeting Selection
            </Button>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
}
