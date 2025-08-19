"use client";

import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Spinner,
  Card,
  CardBody,
  CardHeader,
  Badge,
  Divider,
  Icon,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { FaUsers, FaClock, FaCalendarAlt, FaPlus } from "react-icons/fa";
import { Meeting, CalendarEventResponse } from "../api";
import useApi from "../lib/useApi";
import { useRouter } from "next/navigation";

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
  const [activeMeetings, setActiveMeetings] = useState<Meeting[]>([]);
  const [upcomingEvents, setUpcomingEvents] = useState<CalendarEventResponse[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const api = useApi();
  const router = useRouter();

  useEffect(() => {
    if (!api) return;

    const fetchMeetings = async () => {
      try {
        setLoading(true);

        // Fetch active meetings
        const active = await api.v1RoomsListActiveMeetings({ roomName });
        setActiveMeetings(active);

        // Fetch upcoming calendar events (30 min ahead)
        const upcoming = await api.v1RoomsListUpcomingMeetings({
          roomName,
          minutesAhead: 30,
        });
        setUpcomingEvents(upcoming);

        setError(null);
      } catch (err) {
        console.error("Failed to fetch meetings:", err);
        setError("Failed to load meetings. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();

    // Refresh every 30 seconds
    const interval = setInterval(fetchMeetings, 30000);
    return () => clearInterval(interval);
  }, [api, roomName]);

  const handleJoinMeeting = async (meetingId: string) => {
    if (!api) return;

    try {
      const meeting = await api.v1RoomsJoinMeeting({
        roomName,
        meetingId,
      });
      onMeetingSelect(meeting);
    } catch (err) {
      console.error("Failed to join meeting:", err);
      setError("Failed to join meeting. Please try again.");
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
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch" p={6}>
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
            <VStack spacing={3} mb={6}>
              {activeMeetings.map((meeting) => (
                <Card key={meeting.id} width="100%" variant="outline">
                  <CardBody>
                    <HStack justify="space-between" align="start">
                      <VStack align="start" spacing={2} flex={1}>
                        <HStack>
                          <Icon as={FaCalendarAlt} color="blue.500" />
                          <Text fontWeight="semibold">
                            {meeting.calendar_metadata?.title || "Meeting"}
                          </Text>
                        </HStack>

                        {isOwner && meeting.calendar_metadata?.description && (
                          <Text fontSize="sm" color="gray.600">
                            {meeting.calendar_metadata.description}
                          </Text>
                        )}

                        <HStack spacing={4} fontSize="sm" color="gray.500">
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

                        {isOwner && meeting.calendar_metadata?.attendees && (
                          <HStack spacing={2} flexWrap="wrap">
                            {meeting.calendar_metadata.attendees
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
                            {meeting.calendar_metadata.attendees.length > 3 && (
                              <Badge colorScheme="gray" fontSize="xs">
                                +
                                {meeting.calendar_metadata.attendees.length - 3}{" "}
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
                  </CardBody>
                </Card>
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
            <VStack spacing={3} mb={6}>
              {upcomingEvents.map((event) => (
                <Card
                  key={event.id}
                  width="100%"
                  variant="outline"
                  bg="gray.50"
                >
                  <CardBody>
                    <HStack justify="space-between" align="start">
                      <VStack align="start" spacing={2} flex={1}>
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

                        <HStack spacing={4} fontSize="sm" color="gray.500">
                          <Text>
                            {formatDateTime(event.start_time)} -{" "}
                            {formatDateTime(event.end_time)}
                          </Text>
                        </HStack>

                        {isOwner && event.attendees && (
                          <HStack spacing={2} flexWrap="wrap">
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
                  </CardBody>
                </Card>
              ))}
            </VStack>
          </>
        )}

        <Divider my={6} />

        {/* Create Unscheduled Meeting */}
        <Card width="100%" variant="filled" bg="gray.100">
          <CardBody>
            <HStack justify="space-between" align="center">
              <VStack align="start" spacing={1}>
                <Text fontWeight="semibold">Start an Unscheduled Meeting</Text>
                <Text fontSize="sm" color="gray.600">
                  Create a new meeting room that's not on the calendar
                </Text>
              </VStack>
              <Button
                leftIcon={<FaPlus />}
                colorScheme="green"
                onClick={onCreateUnscheduled}
              >
                Create Meeting
              </Button>
            </HStack>
          </CardBody>
        </Card>
      </Box>
    </VStack>
  );
}
