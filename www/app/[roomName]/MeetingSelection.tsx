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
  useRoomUpcomingMeetings,
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

type Meeting = components["schemas"]["Meeting"];
type CalendarEventResponse = components["schemas"]["CalendarEventResponse"];

interface MeetingSelectionProps {
  roomName: string;
  isOwner: boolean;
  isSharedRoom: boolean;
  onMeetingSelect: (meeting: Meeting) => void;
  onCreateUnscheduled: () => void;
}

export default function MeetingSelection({
  roomName,
  isOwner,
  isSharedRoom,
  onMeetingSelect,
  onCreateUnscheduled,
}: MeetingSelectionProps) {
  const router = useRouter();

  // Use React Query hooks for data fetching
  const roomQuery = useRoomGetByName(roomName);
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const upcomingMeetingsQuery = useRoomUpcomingMeetings(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();
  const deactivateMeetingMutation = useMeetingDeactivate();

  const room = roomQuery.data;

  const activeMeetings = activeMeetingsQuery.data || [];
  const upcomingEvents = upcomingMeetingsQuery.data || [];
  const loading =
    roomQuery.isLoading ||
    activeMeetingsQuery.isLoading ||
    upcomingMeetingsQuery.isLoading;
  const error =
    roomQuery.error || activeMeetingsQuery.error || upcomingMeetingsQuery.error;

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

  const handleJoinUpcoming = async (event: CalendarEventResponse) => {
    // Create an unscheduled meeting for this calendar event
    onCreateUnscheduled();
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
  const displayName = room?.display_name || room?.name || roomName;
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
        displayName={room?.display_name || room?.name}
        showLeaveButton={true}
        onLeave={handleLeaveMeeting}
      />

      <Flex
        flexDir="column"
        w={{ base: "full", md: "container.xl" }}
        mx="auto"
        px={6}
        py={8}
        flex="1"
      >
        {/* Active Meetings */}
        {activeMeetings.length > 0 && (
          <VStack align="stretch" gap={4} mb={6}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Active Meetings
            </Text>
            {activeMeetings.map((meeting) => (
              <Box
                key={meeting.id}
                width="100%"
                bg="white"
                border="1px solid"
                borderColor="gray.200"
                borderRadius="md"
                p={4}
                _hover={{ borderColor: "gray.300" }}
              >
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={2} flex={1}>
                    <HStack>
                      <Icon as={FaCalendarAlt} color="blue.500" />
                      <Text fontWeight="semibold">
                        {(meeting.calendar_metadata as any)?.title || "Meeting"}
                      </Text>
                    </HStack>

                    {isOwner &&
                      (meeting.calendar_metadata as any)?.description && (
                        <Text fontSize="sm" color="gray.600">
                          {(meeting.calendar_metadata as any).description}
                        </Text>
                      )}

                    <HStack gap={4} fontSize="sm" color="gray.500">
                      <HStack>
                        <Icon as={FaUsers} />
                        <Text>{meeting.num_clients} participants</Text>
                      </HStack>
                      <HStack>
                        <Icon as={FaClock} />
                        <Text>
                          Started {formatDateTime(meeting.start_date)}
                        </Text>
                      </HStack>
                    </HStack>

                    {isOwner &&
                      (meeting.calendar_metadata as any)?.attendees && (
                        <HStack gap={2} flexWrap="wrap">
                          {(meeting.calendar_metadata as any).attendees
                            .slice(0, 3)
                            .map((attendee: any, idx: number) => (
                              <Badge
                                key={idx}
                                colorScheme="green"
                                fontSize="xs"
                              >
                                {attendee.name || attendee.email}
                              </Badge>
                            ))}
                          {(meeting.calendar_metadata as any).attendees.length >
                            3 && (
                            <Badge colorScheme="gray" fontSize="xs">
                              +
                              {(meeting.calendar_metadata as any).attendees
                                .length - 3}{" "}
                              more
                            </Badge>
                          )}
                        </HStack>
                      )}
                  </VStack>

                  <HStack gap={2}>
                    <Button
                      colorScheme="blue"
                      size="md"
                      onClick={() => handleJoinMeeting(meeting.id)}
                    >
                      Join Now
                    </Button>
                    {isOwner && (
                      <Button
                        variant="outline"
                        colorScheme="red"
                        size="md"
                        onClick={() => handleEndMeeting(meeting.id)}
                        isLoading={deactivateMeetingMutation.isPending}
                      >
                        <Icon as={LuX} />
                        End Meeting
                      </Button>
                    )}
                  </HStack>
                </HStack>
              </Box>
            ))}
          </VStack>
        )}

        {/* Upcoming Meetings */}
        {upcomingEvents.length > 0 && (
          <VStack align="stretch" gap={4} mb={6}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Upcoming Meetings
            </Text>
            {upcomingEvents.map((event) => {
              const now = new Date();
              const startTime = new Date(event.start_time);
              const endTime = new Date(event.end_time);
              const isOngoing = startTime <= now && now <= endTime;
              const minutesUntilStart = Math.floor(
                (startTime.getTime() - now.getTime()) / (1000 * 60),
              );
              const canJoinEarly = minutesUntilStart <= 5; // Allow joining 5 minutes before

              return (
                <Box
                  key={event.id}
                  width="100%"
                  bg="white"
                  border="1px solid"
                  borderColor="gray.200"
                  borderRadius="md"
                  p={4}
                  _hover={{ borderColor: "gray.300" }}
                >
                  <HStack justify="space-between" align="start">
                    <VStack align="start" gap={2} flex={1}>
                      <HStack>
                        <Icon
                          as={FaCalendarAlt}
                          color={isOngoing ? "blue.500" : "orange.500"}
                        />
                        <Text fontWeight="semibold">
                          {event.title || "Scheduled Meeting"}
                        </Text>
                        <Badge
                          colorScheme={isOngoing ? "blue" : "orange"}
                          fontSize="xs"
                        >
                          {isOngoing
                            ? formatStartedAgo(event.start_time)
                            : formatCountdown(event.start_time)}
                        </Badge>
                      </HStack>

                      {isOwner && event.description && (
                        <Text fontSize="sm" color="gray.600">
                          {event.description}
                        </Text>
                      )}

                      <HStack gap={4} fontSize="sm" color="gray.500">
                        <Text>
                          {formatDateTime(event.start_time)} -{" "}
                          {formatDateTime(event.end_time)}
                        </Text>
                      </HStack>

                      {isOwner && event.attendees && (
                        <HStack gap={2} flexWrap="wrap">
                          {event.attendees
                            .slice(0, 3)
                            .map((attendee: any, idx: number) => (
                              <Badge
                                key={idx}
                                colorScheme="purple"
                                fontSize="xs"
                              >
                                {attendee.name || attendee.email}
                              </Badge>
                            ))}
                          {event.attendees.length > 3 && (
                            <Badge colorScheme="gray" fontSize="xs">
                              +{event.attendees.length - 3} more
                            </Badge>
                          )}
                        </HStack>
                      )}
                    </VStack>

                    <Button
                      variant="outline"
                      colorScheme={isOngoing || canJoinEarly ? "blue" : "gray"}
                      size="md"
                      onClick={() => handleJoinUpcoming(event)}
                      isDisabled={!isOngoing && !canJoinEarly}
                    >
                      Join
                    </Button>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
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

        {/* Message for non-owners of private rooms */}
        {!isOwner && !isSharedRoom && (
          <Box
            width="100%"
            bg="gray.50"
            border="1px solid"
            borderColor="gray.200"
            borderRadius="md"
            p={4}
            mt={6}
          >
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Only the room owner can create unscheduled meetings in this
              private room.
            </Text>
          </Box>
        )}
      </Flex>
    </Flex>
  );
}
