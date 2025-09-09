"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Spinner,
  Text,
  VStack,
  Button,
  HStack,
  Badge,
} from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useRoomGetByName } from "../../../lib/apiHooks";
import MinimalHeader from "../../../components/MinimalHeader";

interface WaitPageClientProps {
  params: {
    roomName: string;
    eventId: string;
  };
}

const formatDateTime = (date: string | Date) => {
  const d = new Date(date);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatCountdown = (startTime: string | Date) => {
  const now = new Date();
  const start = new Date(startTime);
  const diff = start.getTime() - now.getTime();

  if (diff <= 0) return "Meeting should start now";

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `Starts in ${days}d ${hours % 24}h ${minutes % 60}m`;
  if (hours > 0) return `Starts in ${hours}h ${minutes % 60}m`;
  return `Starts in ${minutes} minutes`;
};

export default function WaitPageClient({ params }: WaitPageClientProps) {
  const { roomName, eventId } = params;
  const router = useRouter();

  const [countdown, setCountdown] = useState<string>("");

  // Fetch room data
  const roomQuery = useRoomGetByName(roomName);
  const room = roomQuery.data;

  // Mock event data - in a real implementation, you'd fetch the actual event
  const mockEvent = {
    id: eventId,
    title: "Upcoming Meeting",
    start_time: new Date(Date.now() + 15 * 60 * 1000), // 15 minutes from now
    end_time: new Date(Date.now() + 75 * 60 * 1000), // 1 hour 15 minutes from now
    description: "Meeting will start soon",
  };

  // Update countdown every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(formatCountdown(mockEvent.start_time));
    }, 1000);

    return () => clearInterval(timer);
  }, [mockEvent.start_time]);

  // Redirect to selection if room not found
  useEffect(() => {
    if (roomQuery.isError) {
      router.push(`/${roomName}`);
    }
  }, [roomQuery.isError, router, roomName]);

  const handleJoinEarly = () => {
    // In a real implementation, this would create a meeting and join
    alert("Join early functionality not yet implemented");
  };

  const handleBackToSelection = () => {
    router.push(`/${roomName}`);
  };

  if (roomQuery.isLoading) {
    return (
      <Box display="flex" flexDirection="column" minH="100vh">
        <MinimalHeader
          roomName={roomName}
          displayName={room?.display_name || room?.name}
          showLeaveButton={false}
        />
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          flex="1"
          p={4}
        >
          <VStack gap={4}>
            <Spinner color="blue.500" size="xl" />
            <Text fontSize="lg">Loading...</Text>
          </VStack>
        </Box>
      </Box>
    );
  }

  return (
    <Box display="flex" flexDirection="column" minH="100vh">
      <MinimalHeader
        roomName={roomName}
        displayName={room?.display_name || room?.name}
      />

      <Box flex="1" p={4}>
        <VStack gap={6} align="stretch" maxW="container.md" mx="auto" pt={8}>
          <Box textAlign="center">
            <Text fontSize="3xl" fontWeight="bold" mb={2}>
              {mockEvent.title}
            </Text>
            <Badge colorScheme="orange" fontSize="lg" px={4} py={2}>
              {countdown}
            </Badge>
          </Box>

          <Box
            bg="white"
            borderRadius="md"
            p={8}
            textAlign="center"
            boxShadow="sm"
          >
            <VStack gap={6}>
              <VStack gap={2}>
                <Text fontSize="lg" fontWeight="semibold">
                  Meeting Details
                </Text>
                <Text color="gray.600">
                  {formatDateTime(mockEvent.start_time)} -{" "}
                  {formatDateTime(mockEvent.end_time)}
                </Text>
                {mockEvent.description && (
                  <Text fontSize="sm" color="gray.500">
                    {mockEvent.description}
                  </Text>
                )}
              </VStack>

              <Box h="1px" bg="gray.200" w="100%" />

              <VStack gap={4}>
                <Text fontSize="md" color="gray.600">
                  The meeting hasn't started yet. You can wait here or come back
                  later.
                </Text>

                <HStack gap={4}>
                  <Button
                    colorScheme="blue"
                    onClick={handleJoinEarly}
                    size="lg"
                  >
                    Join Early
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleBackToSelection}
                    size="lg"
                  >
                    Back to Meetings
                  </Button>
                </HStack>
              </VStack>
            </VStack>
          </Box>
        </VStack>
      </Box>
    </Box>
  );
}
