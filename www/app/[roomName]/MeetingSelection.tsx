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
} from "@chakra-ui/react";
import React from "react";
import { FaUsers, FaClock, FaCalendarAlt, FaPlus } from "react-icons/fa";
import type { components } from "../reflector-api";
import {
  useRoomActiveMeetings,
  useRoomUpcomingMeetings,
  useRoomJoinMeeting,
} from "../lib/apiHooks";
import { useRouter } from "next/navigation";

type Meeting = components["schemas"]["Meeting"];
type CalendarEventResponse = components["schemas"]["CalendarEventResponse"];

interface MeetingSelectionProps {
  roomName: string;
  isOwner: boolean;
  onMeetingSelect: (meeting: Meeting) => void;
  onCreateUnscheduled: () => void;
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

  if (diff <= 0) return "Starting now";

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `Starts in ${hours}h ${minutes % 60}m`;
  }
  return `Starts in ${minutes} minutes`;
};

export default function MeetingSelection({
  roomName,
  isOwner,
  onMeetingSelect,
  onCreateUnscheduled,
}: MeetingSelectionProps) {
  const router = useRouter();

  // Use React Query hooks for data fetching
  const activeMeetingsQuery = useRoomActiveMeetings(roomName);
  const upcomingMeetingsQuery = useRoomUpcomingMeetings(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();

  const activeMeetings = activeMeetingsQuery.data || [];
  const upcomingEvents = upcomingMeetingsQuery.data || [];
  const loading =
    activeMeetingsQuery.isLoading || upcomingMeetingsQuery.isLoading;
  const error = activeMeetingsQuery.error || upcomingMeetingsQuery.error;

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

  const handleJoinUpcoming = (event: CalendarEventResponse) => {
    // Navigate to waiting page with event info
    router.push(`/room/${roomName}/wait?eventId=${event.id}`);
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

  return (
    <VStack gap={6} align="stretch" p={6}>
      <Box>
        <Text fontSize="2xl" fontWeight="bold" mb={4}>
          Select a Meeting
        </Text>

        {/* Active Meetings */}
        {activeMeetings.length > 0 && (
          <>
            <Text fontSize="lg" fontWeight="semibold" mb={3}>
              Active Meetings
            </Text>
            <VStack gap={3} mb={6}>
              {activeMeetings.map((meeting) => (
                <Box
                  key={meeting.id}
                  width="100%"
                  border="1px solid"
                  borderColor="gray.200"
                  borderRadius="md"
                  p={4}
                >
                  <HStack justify="space-between" align="start">
                    <VStack align="start" gap={2} flex={1}>
                      <HStack>
                        <Icon as={FaCalendarAlt} color="blue.500" />
                        <Text fontWeight="semibold">
                          {(meeting.calendar_metadata as any)?.title ||
                            "Meeting"}
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
                            {(meeting.calendar_metadata as any).attendees
                              .length > 3 && (
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

                    <Button
                      colorScheme="blue"
                      size="md"
                      onClick={() => handleJoinMeeting(meeting.id)}
                    >
                      Join Now
                    </Button>
                  </HStack>
                </Box>
              ))}
            </VStack>
          </>
        )}

        {/* Upcoming Meetings */}
        {upcomingEvents.length > 0 && (
          <>
            <Text fontSize="lg" fontWeight="semibold" mb={3}>
              Upcoming Meetings
            </Text>
            <VStack gap={3} mb={6}>
              {upcomingEvents.map((event) => (
                <Box
                  key={event.id}
                  width="100%"
                  border="1px solid"
                  borderColor="gray.200"
                  borderRadius="md"
                  p={4}
                  bg="gray.50"
                >
                  <HStack justify="space-between" align="start">
                    <VStack align="start" gap={2} flex={1}>
                      <HStack>
                        <Icon as={FaCalendarAlt} color="orange.500" />
                        <Text fontWeight="semibold">
                          {event.title || "Scheduled Meeting"}
                        </Text>
                        <Badge colorScheme="orange" fontSize="xs">
                          {formatCountdown(event.start_time)}
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
                      colorScheme="orange"
                      size="md"
                      onClick={() => handleJoinUpcoming(event)}
                    >
                      Join Early
                    </Button>
                  </HStack>
                </Box>
              ))}
            </VStack>
          </>
        )}

        <Box h="1px" bg="gray.200" my={6} />

        {/* Create Unscheduled Meeting */}
        <Box width="100%" bg="gray.100" borderRadius="md" p={4}>
          <HStack justify="space-between" align="center">
            <VStack align="start" gap={1}>
              <Text fontWeight="semibold">Start an Unscheduled Meeting</Text>
              <Text fontSize="sm" color="gray.600">
                Create a new meeting room that's not on the calendar
              </Text>
            </VStack>
            <Button colorScheme="green" onClick={onCreateUnscheduled}>
              <FaPlus />
              Create Meeting
            </Button>
          </HStack>
        </Box>
      </Box>
    </VStack>
  );
}
