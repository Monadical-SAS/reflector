"use client";

import { useEffect, useState } from "react";
import { Box, Spinner, Text, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useRoomGetByName } from "../../lib/apiHooks";
import MinimalHeader from "../../components/MinimalHeader";
interface MeetingPageProps {
  params: {
    roomName: string;
    meetingId: string;
  };
}

export default function MeetingPage({ params }: MeetingPageProps) {
  const { roomName, meetingId } = params;
  const router = useRouter();

  // Fetch room data
  const roomQuery = useRoomGetByName(roomName);

  const room = roomQuery.data;
  const isLoading = roomQuery.isLoading;
  const error = roomQuery.error;

  // Redirect to selection if room not found
  useEffect(() => {
    if (roomQuery.isError) {
      router.push(`/${roomName}`);
    }
  }, [roomQuery.isError, router, roomName]);

  if (isLoading) {
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
          bg="gray.50"
          p={4}
        >
          <VStack gap={4}>
            <Spinner color="blue.500" size="xl" />
            <Text fontSize="lg">Loading meeting...</Text>
          </VStack>
        </Box>
      </Box>
    );
  }

  if (error || !room) {
    return (
      <Box display="flex" flexDirection="column" minH="100vh">
        <MinimalHeader
          roomName={roomName}
          displayName={room?.display_name || room?.name}
        />
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          flex="1"
          bg="gray.50"
          p={4}
        >
          <Text fontSize="lg">Meeting not found</Text>
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

      <Box flex="1" bg="gray.50" p={4}>
        <VStack gap={4} align="stretch" maxW="container.lg" mx="auto">
          <Text fontSize="2xl" fontWeight="bold" textAlign="center">
            Meeting Room
          </Text>

          <Box
            bg="white"
            borderRadius="md"
            p={6}
            textAlign="center"
            minH="400px"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <VStack gap={4}>
              <Text fontSize="lg" color="gray.600">
                Meeting Interface Coming Soon
              </Text>
              <Text fontSize="sm" color="gray.500">
                This is where the video call, transcription, and meeting
                controls will be displayed.
              </Text>
              <Text fontSize="sm" color="gray.500">
                Meeting ID: {meetingId}
              </Text>
            </VStack>
          </Box>
        </VStack>
      </Box>
    </Box>
  );
}
