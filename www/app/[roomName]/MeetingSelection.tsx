"use client";

import { partition } from "remeda";
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
import { formatDateTime, formatStartedAgo } from "../lib/timeUtils";
import MeetingMinimalHeader from "../components/MeetingMinimalHeader";

type Meeting = components["schemas"]["Meeting"];

interface MeetingSelectionProps {
  roomName: string;
  isOwner: boolean;
  isSharedRoom: boolean;
  authLoading: boolean;
  onMeetingSelect: (meeting: Meeting) => void;
  onCreateUnscheduled: () => void;
  isCreatingMeeting?: boolean;
}

export default function MeetingSelection({
  roomName,
  isOwner,
  isSharedRoom,
  onMeetingSelect,
  onCreateUnscheduled,
  isCreatingMeeting = false,
}: MeetingSelectionProps) {
  const router = useRouter();

  const roomQuery = useRoomGetByName(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();
  const deactivateMeetingMutation = useMeetingDeactivate();

  const room = roomQuery.data;
  const allMeetings = activeMeetingsQuery.data || [];

  const now = new Date();
  const [currentMeetings, nonCurrentMeetings] = partition(
    allMeetings,
    (meeting) => {
      const startTime = new Date(meeting.start_date);
      const endTime = new Date(meeting.end_date);
      // Meeting is ongoing if current time is between start and end
      return now >= startTime && now <= endTime;
    },
  );

  const upcomingMeetings = nonCurrentMeetings.filter((meeting) => {
    const startTime = new Date(meeting.start_date);
    // Meeting is upcoming if it hasn't started yet
    return now < startTime;
  });

  const loading = roomQuery.isLoading || activeMeetingsQuery.isLoading;
  const error = roomQuery.error || activeMeetingsQuery.error;

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

  const handleLeaveMeeting = () => {
    router.push("/");
  };

  return (
    <Flex flexDir="column" minH="100vh" position="relative">
      {/* Loading overlay */}
      {isCreatingMeeting && (
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg="blackAlpha.600"
          zIndex={9999}
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <VStack gap={4} p={8} bg="white" borderRadius="lg" boxShadow="xl">
            <Spinner size="lg" color="blue.500" />
            <Text fontSize="lg" fontWeight="medium">
              Creating meeting...
            </Text>
          </VStack>
        </Box>
      )}

      <MeetingMinimalHeader
        roomName={roomName}
        displayName={room?.name}
        showLeaveButton={true}
        onLeave={handleLeaveMeeting}
        showCreateButton={isOwner || isSharedRoom}
        onCreateMeeting={onCreateUnscheduled}
        isCreatingMeeting={isCreatingMeeting}
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
        {currentMeetings.length > 0 ? (
          <VStack align="stretch" gap={6} mb={8}>
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
                          Started{" "}
                          {formatStartedAgo(new Date(meeting.start_date))}
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
        ) : upcomingMeetings.length > 0 ? (
          /* Upcoming Meetings - BIG DISPLAY when no ongoing meetings */
          <VStack align="stretch" gap={6} mb={8}>
            <Text fontSize="xl" fontWeight="bold" color="gray.800">
              Upcoming Meeting{upcomingMeetings.length > 1 ? "s" : ""}
            </Text>
            {upcomingMeetings.map((meeting) => {
              const now = new Date();
              const startTime = new Date(meeting.start_date);
              const minutesUntilStart = Math.floor(
                (startTime.getTime() - now.getTime()) / (1000 * 60),
              );

              return (
                <Box
                  key={meeting.id}
                  width="100%"
                  bg="orange.50"
                  borderRadius="xl"
                  p={8}
                  border="2px solid"
                  borderColor="orange.200"
                >
                  <HStack justify="space-between" align="start">
                    <VStack align="start" gap={4} flex={1}>
                      <HStack>
                        <Icon
                          as={FaCalendarAlt}
                          color="orange.600"
                          boxSize="24px"
                        />
                        <Text
                          fontSize="2xl"
                          fontWeight="bold"
                          color="orange.800"
                        >
                          {(meeting.calendar_metadata as any)?.title ||
                            "Upcoming Meeting"}
                        </Text>
                      </HStack>

                      {isOwner &&
                        (meeting.calendar_metadata as any)?.description && (
                          <Text fontSize="lg" color="gray.700">
                            {(meeting.calendar_metadata as any).description}
                          </Text>
                        )}

                      <HStack gap={8} fontSize="md" color="gray.600">
                        <Badge colorScheme="orange" fontSize="md" px={3} py={1}>
                          Starts in {minutesUntilStart} minute
                          {minutesUntilStart !== 1 ? "s" : ""}
                        </Badge>
                        <Text>{formatDateTime(meeting.start_date)}</Text>
                      </HStack>

                      {isOwner &&
                        (meeting.calendar_metadata as any)?.attendees && (
                          <HStack gap={3} flexWrap="wrap">
                            {(meeting.calendar_metadata as any).attendees
                              .slice(0, 4)
                              .map((attendee: any, idx: number) => (
                                <Badge
                                  key={idx}
                                  colorScheme="orange"
                                  fontSize="sm"
                                  px={3}
                                  py={1}
                                >
                                  {attendee.name || attendee.email}
                                </Badge>
                              ))}
                            {(meeting.calendar_metadata as any).attendees
                              .length > 4 && (
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
                        colorScheme="orange"
                        size="xl"
                        fontSize="lg"
                        px={8}
                        py={6}
                        onClick={() => handleJoinUpcoming(meeting)}
                      >
                        <Icon as={FaClock} boxSize="20px" me={2} />
                        Join Early
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
                          Cancel Meeting
                        </Button>
                      )}
                    </VStack>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
        ) : null}

        {/* Upcoming Meetings - SMALLER ASIDE DISPLAY when there are ongoing meetings */}
        {currentMeetings.length > 0 && upcomingMeetings.length > 0 && (
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
                        Starts: {formatDateTime(new Date(meeting.start_date))}
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
          <Flex
            width="100%"
            flex="1"
            justify="center"
            align="center"
            textAlign="center"
            mb={6}
          >
            <VStack gap={4}>
              <Icon as={FaCalendarAlt} boxSize="48px" color="gray.400" />
              <VStack gap={2}>
                <Text fontSize="xl" fontWeight="semibold" color="black">
                  No meetings right now
                </Text>
                <Text fontSize="md" color="gray.600" maxW="400px">
                  There are no ongoing or upcoming meetings in this room at the
                  moment.
                </Text>
              </VStack>
            </VStack>
          </Flex>
        )}
      </Flex>
    </Flex>
  );
}
