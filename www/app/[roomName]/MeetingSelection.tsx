"use client";

import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Spinner,
  Badge,
  Icon,
  Flex,
} from "@chakra-ui/react";
import React from "react";
import { FaUsers, FaClock, FaCalendarAlt, FaPlus } from "react-icons/fa";
import { LuX } from "react-icons/lu";
import type { components } from "../reflector-api";
import {
  useRoomActiveMeetings,
  useRoomJoinMeeting,
  useMeetingDeactivate,
  useRoomGetByName,
} from "../lib/apiHooks";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  formatDateTime,
  formatCountdown,
  formatStartedAgo,
} from "../lib/timeUtils";
import MinimalHeader from "../components/MinimalHeader";

// Meeting join settings
const EARLY_JOIN_MINUTES = 5; // Allow joining 5 minutes before meeting starts

type Meeting = components["schemas"]["Meeting"];

interface MeetingSelectionProps {
  roomName: string;
  isOwner: boolean;
  isSharedRoom: boolean;
  authLoading: boolean;
  onMeetingSelect: (meeting: Meeting) => void;
  onCreateUnscheduled: () => void;
}

export default function MeetingSelection({
  roomName,
  isOwner,
  isSharedRoom,
  authLoading,
  onMeetingSelect,
  onCreateUnscheduled,
}: MeetingSelectionProps) {
  const router = useRouter();

  // Use React Query hooks for data fetching
  const roomQuery = useRoomGetByName(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();
  const deactivateMeetingMutation = useMeetingDeactivate();

  const room = roomQuery.data;
  const allMeetings = activeMeetingsQuery.data || [];

  // Separate current ongoing meetings from upcoming meetings (created by worker, within 5 minutes)
  const now = new Date();
  const currentMeetings = allMeetings.filter((meeting) => {
    const startTime = new Date(meeting.start_date);
    // Meeting is ongoing if it started and participants have joined or it's been running for a while
    return (
      meeting.num_clients > 0 || now.getTime() - startTime.getTime() > 60000
    ); // 1 minute threshold
  });

  const upcomingMeetings = allMeetings.filter((meeting) => {
    const startTime = new Date(meeting.start_date);
    const minutesUntilStart = Math.floor(
      (startTime.getTime() - now.getTime()) / (1000 * 60),
    );
    // Show meetings that start within 5 minutes and haven't started yet
    return (
      minutesUntilStart <= EARLY_JOIN_MINUTES &&
      minutesUntilStart > 0 &&
      meeting.num_clients === 0
    );
  });
  const loading = roomQuery.isLoading || activeMeetingsQuery.isLoading;
  const error = roomQuery.error || activeMeetingsQuery.error;

  const handleJoinMeeting = async (meetingId: string) => {
    try {
      const meeting = await joinMeetingMutation.mutateAsync({
        params: {
          path: {
            room_name: roomName,
            meeting_id: meetingId,
          },
        },
      });
      onMeetingSelect(meeting);
    } catch (err) {
      console.error("Failed to join meeting:", err);
      // Handle error appropriately since we don't have setError anymore
    }
  };

  const handleJoinUpcoming = async (meeting: Meeting) => {
    // Join the upcoming meeting and navigate to local meeting page
    try {
      const joinedMeeting = await joinMeetingMutation.mutateAsync({
        params: {
          path: {
            room_name: roomName,
            meeting_id: meeting.id,
          },
        },
      });
      onMeetingSelect(joinedMeeting);
    } catch (err) {
      console.error("Failed to join upcoming meeting:", err);
    }
  };

  const handleJoinDirect = (meeting: Meeting) => {
    // Navigate to local meeting page instead of external URL
    onMeetingSelect(meeting);
  };

  const handleEndMeeting = async (meetingId: string) => {
    try {
      await deactivateMeetingMutation.mutateAsync({
        params: {
          path: {
            meeting_id: meetingId,
          },
        },
      });
    } catch (err) {
      console.error("Failed to end meeting:", err);
    }
  };

  if (loading) {
    return (
      <Box p={8} textAlign="center">
        <Spinner size="lg" color="blue.500" />
        <Text mt={4}>Loading meetings...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        p={4}
        borderRadius="md"
        bg="red.50"
        borderLeft="4px solid"
        borderColor="red.400"
      >
        <Text fontWeight="semibold" color="red.800">
          Error
        </Text>
        <Text color="red.700">{"Failed to load meetings"}</Text>
      </Box>
    );
  }

  // Generate display name for room
  const displayName = room?.name || roomName;
  const roomTitle =
    displayName.endsWith("'s") || displayName.endsWith("s")
      ? `${displayName} Room`
      : `${displayName}'s Room`;

  const handleLeaveMeeting = () => {
    router.push("/");
  };

  return (
    <Flex flexDir="column" minH="100vh">
      <MinimalHeader
        roomName={roomName}
        displayName={room?.name}
        showLeaveButton={true}
        onLeave={handleLeaveMeeting}
      />

      <Flex
        flexDir="column"
        w="full"
        maxW="800px"
        mx="auto"
        px={6}
        py={8}
        flex="1"
        gap={6}
      >
        {/* Current Ongoing Meetings - BIG DISPLAY */}
        {currentMeetings.length > 0 && (
          <VStack align="stretch" gap={6} mb={8}>
            <Text fontSize="xl" fontWeight="bold" color="gray.800">
              Live Meeting{currentMeetings.length > 1 ? "s" : ""}
            </Text>
            {currentMeetings.map((meeting) => (
              <Box
                key={meeting.id}
                width="100%"
                bg="gray.50"
                borderRadius="xl"
                p={8}
              >
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={4} flex={1}>
                    <HStack>
                      <Icon
                        as={FaCalendarAlt}
                        color="blue.600"
                        boxSize="24px"
                      />
                      <Text fontSize="2xl" fontWeight="bold" color="blue.800">
                        {(meeting.calendar_metadata as any)?.title ||
                          "Live Meeting"}
                      </Text>
                    </HStack>

                    {isOwner &&
                      (meeting.calendar_metadata as any)?.description && (
                        <Text fontSize="lg" color="gray.700">
                          {(meeting.calendar_metadata as any).description}
                        </Text>
                      )}

                    <HStack gap={8} fontSize="md" color="gray.600">
                      <HStack>
                        <Icon as={FaUsers} boxSize="20px" />
                        <Text fontWeight="medium">
                          {meeting.num_clients} participants
                        </Text>
                      </HStack>
                      <HStack>
                        <Icon as={FaClock} boxSize="20px" />
                        <Text>
                          Started {formatStartedAgo(meeting.start_date)}
                        </Text>
                      </HStack>
                    </HStack>

                    {isOwner &&
                      (meeting.calendar_metadata as any)?.attendees && (
                        <HStack gap={3} flexWrap="wrap">
                          {(meeting.calendar_metadata as any).attendees
                            .slice(0, 4)
                            .map((attendee: any, idx: number) => (
                              <Badge
                                key={idx}
                                colorScheme="blue"
                                fontSize="sm"
                                px={3}
                                py={1}
                              >
                                {attendee.name || attendee.email}
                              </Badge>
                            ))}
                          {(meeting.calendar_metadata as any).attendees.length >
                            4 && (
                            <Badge
                              colorScheme="gray"
                              fontSize="sm"
                              px={3}
                              py={1}
                            >
                              +
                              {(meeting.calendar_metadata as any).attendees
                                .length - 4}{" "}
                              more
                            </Badge>
                          )}
                        </HStack>
                      )}
                  </VStack>

                  <VStack gap={3}>
                    <Button
                      colorScheme="blue"
                      size="xl"
                      fontSize="lg"
                      px={8}
                      py={6}
                      onClick={() => handleJoinDirect(meeting)}
                    >
                      <Icon as={FaUsers} boxSize="20px" me={2} />
                      Join Now
                    </Button>
                    {isOwner && (
                      <Button
                        variant="outline"
                        colorScheme="red"
                        size="md"
                        onClick={() => handleEndMeeting(meeting.id)}
                        loading={deactivateMeetingMutation.isPending}
                      >
                        <Icon as={LuX} me={2} />
                        End Meeting
                      </Button>
                    )}
                  </VStack>
                </HStack>
              </Box>
            ))}
          </VStack>
        )}

        {/* Upcoming Meetings - SMALLER ASIDE DISPLAY */}
        {upcomingMeetings.length > 0 && (
          <VStack align="stretch" gap={4} mb={6}>
            <Text fontSize="lg" fontWeight="semibold" color="gray.700">
              Starting Soon
            </Text>
            <HStack gap={4} flexWrap="wrap">
              {upcomingMeetings.map((meeting) => {
                const now = new Date();
                const startTime = new Date(meeting.start_date);
                const minutesUntilStart = Math.floor(
                  (startTime.getTime() - now.getTime()) / (1000 * 60),
                );

                return (
                  <Box
                    key={meeting.id}
                    bg="white"
                    border="2px solid"
                    borderColor="orange.200"
                    borderRadius="lg"
                    p={4}
                    minW="300px"
                    maxW="400px"
                    _hover={{ borderColor: "orange.300", bg: "orange.50" }}
                    transition="all 0.2s"
                  >
                    <VStack align="start" gap={3}>
                      <HStack>
                        <Icon as={FaCalendarAlt} color="orange.500" />
                        <Text fontWeight="semibold" fontSize="md">
                          {(meeting.calendar_metadata as any)?.title ||
                            "Upcoming Meeting"}
                        </Text>
                      </HStack>

                      <Badge colorScheme="orange" fontSize="sm" px={2} py={1}>
                        in {minutesUntilStart} minute
                        {minutesUntilStart !== 1 ? "s" : ""}
                      </Badge>

                      <Text fontSize="sm" color="gray.600">
                        Starts: {formatDateTime(meeting.start_date)}
                      </Text>

                      <Button
                        colorScheme="orange"
                        size="sm"
                        width="full"
                        onClick={() => handleJoinUpcoming(meeting)}
                      >
                        Join Early
                      </Button>
                    </VStack>
                  </Box>
                );
              })}
            </HStack>
          </VStack>
        )}

        {/* No meetings message - show when no ongoing or upcoming meetings */}
        {currentMeetings.length === 0 && upcomingMeetings.length === 0 && (
          <Box
            width="100%"
            bg="gray.50"
            borderRadius="xl"
            p={8}
            textAlign="center"
            mb={6}
          >
            <VStack gap={4}>
              <Icon as={FaCalendarAlt} boxSize="48px" color="gray.400" />
              <VStack gap={2}>
                <Text fontSize="xl" fontWeight="semibold" color="gray.700">
                  No meetings right now
                </Text>
                <Text fontSize="md" color="gray.600" maxW="400px">
                  There are no ongoing or upcoming meetings in this room at the moment.
                  {(isOwner || isSharedRoom) && " You can start a quick meeting below."}
                </Text>
              </VStack>
            </VStack>
          </Box>
        )}

        {/* Create Unscheduled Meeting - Only for room owners or shared rooms */}
        {(isOwner || isSharedRoom) && (
          <Box width="100%" bg="gray.50" borderRadius="md" p={4} mt={6}>
            <HStack justify="space-between" align="center">
              <VStack align="start" gap={1}>
                <Text fontWeight="semibold">Start a Quick Meeting</Text>
                <Text fontSize="sm" color="gray.600">
                  Jump into a meeting room right away
                </Text>
              </VStack>
              <Button colorScheme="green" onClick={onCreateUnscheduled}>
                Create Meeting
              </Button>
            </HStack>
          </Box>
        )}
      </Flex>
    </Flex>
  );
}
