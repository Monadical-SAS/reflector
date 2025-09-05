"use client";

import {
  Box,
  VStack,
  Heading,
  Text,
  HStack,
  Badge,
  Spinner,
  Flex,
  Link,
  Button,
  IconButton,
  Tooltip,
  Wrap,
} from "@chakra-ui/react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { FaSync, FaClock, FaUsers, FaEnvelope } from "react-icons/fa";
import { LuArrowLeft } from "react-icons/lu";
import {
  useRoomCalendarEvents,
  useRoomIcsSync,
} from "../../../../lib/apiHooks";
import type { components } from "../../../../reflector-api";

type CalendarEventResponse = components["schemas"]["CalendarEventResponse"];

export default function RoomCalendarPage() {
  const params = useParams();
  const router = useRouter();
  const roomName = params.roomName as string;

  const [syncing, setSyncing] = useState(false);

  // React Query hooks
  const eventsQuery = useRoomCalendarEvents(roomName);
  const syncMutation = useRoomIcsSync();

  const events = eventsQuery.data || [];
  const loading = eventsQuery.isLoading;
  const error = eventsQuery.error ? "Failed to load calendar events" : null;

  const handleSync = async () => {
    try {
      setSyncing(true);
      await syncMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
      });
      // Refetch events after sync
      await eventsQuery.refetch();
    } catch (err: any) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  const formatEventTime = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const options: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
    };

    const dateOptions: Intl.DateTimeFormatOptions = {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    };

    const isSameDay = startDate.toDateString() === endDate.toDateString();

    if (isSameDay) {
      return `${startDate.toLocaleDateString(undefined, dateOptions)} • ${startDate.toLocaleTimeString(undefined, options)} - ${endDate.toLocaleTimeString(undefined, options)}`;
    } else {
      return `${startDate.toLocaleDateString(undefined, dateOptions)} ${startDate.toLocaleTimeString(undefined, options)} - ${endDate.toLocaleDateString(undefined, dateOptions)} ${endDate.toLocaleTimeString(undefined, options)}`;
    }
  };

  const isEventActive = (start: string, end: string) => {
    const now = new Date();
    const startDate = new Date(start);
    const endDate = new Date(end);
    return now >= startDate && now <= endDate;
  };

  const isEventUpcoming = (start: string) => {
    const now = new Date();
    const startDate = new Date(start);
    const hourFromNow = new Date(now.getTime() + 60 * 60 * 1000);
    return startDate > now && startDate <= hourFromNow;
  };

  const getAttendeeDisplay = (attendee: any) => {
    // Use name if available, otherwise use email
    const displayName = attendee.name || attendee.email || "Unknown";
    // Extract just the name part if it's in "Name <email>" format
    const cleanName = displayName.replace(/<.*>/, "").trim();
    return cleanName;
  };

  const getAttendeeEmail = (attendee: any) => {
    return attendee.email || "";
  };

  const renderAttendees = (attendees: any[]) => {
    if (!attendees || attendees.length === 0) return null;

    return (
      <HStack fontSize="sm" color="gray.600" flexWrap="wrap">
        <FaUsers />
        <Text>Attendees:</Text>
        <Wrap gap={2}>
          {attendees.map((attendee, index) => {
            const email = getAttendeeEmail(attendee);
            const display = getAttendeeDisplay(attendee);

            if (email && email !== display) {
              return (
                <Tooltip
                  key={index}
                  content={
                    <HStack>
                      <FaEnvelope size="12" />
                      <Text>{email}</Text>
                    </HStack>
                  }
                >
                  <Badge variant="subtle" colorPalette="blue" cursor="help">
                    {display}
                  </Badge>
                </Tooltip>
              );
            } else {
              return (
                <Badge key={index} variant="subtle" colorPalette="blue">
                  {display}
                </Badge>
              );
            }
          })}
        </Wrap>
      </HStack>
    );
  };

  const sortedEvents = [...events].sort(
    (a, b) =>
      new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
  );

  // Separate events by status
  const now = new Date();
  const activeEvents = sortedEvents.filter((e) =>
    isEventActive(e.start_time, e.end_time),
  );
  const upcomingEvents = sortedEvents.filter(
    (e) => new Date(e.start_time) > now,
  );
  const pastEvents = sortedEvents
    .filter((e) => new Date(e.end_time) < now)
    .reverse();

  return (
    <Box w={{ base: "full", md: "container.xl" }} mx="auto" pt={2}>
      <VStack align="stretch" gap={6}>
        <Flex justify="space-between" align="center">
          <HStack gap={3}>
            <IconButton
              aria-label="Back to rooms"
              title="Back to rooms"
              size="sm"
              variant="ghost"
              onClick={() => router.push("/rooms")}
            >
              <LuArrowLeft />
            </IconButton>
            <Heading size="lg">Calendar for {roomName}</Heading>
          </HStack>
          <Button colorPalette="blue" onClick={handleSync} disabled={syncing}>
            {syncing ? <Spinner size="sm" /> : <FaSync />}
            Force Sync
          </Button>
        </Flex>

        {error && (
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
            <Text color="red.700">{error}</Text>
          </Box>
        )}

        {loading ? (
          <Flex justify="center" py={8}>
            <Spinner size="xl" />
          </Flex>
        ) : events.length === 0 ? (
          <Box bg="white" borderRadius="lg" boxShadow="md" p={6}>
            <Text textAlign="center" color="gray.500">
              No calendar events found. Make sure your calendar is configured
              and synced.
            </Text>
          </Box>
        ) : (
          <VStack align="stretch" gap={6}>
            {/* Active Events */}
            {activeEvents.length > 0 && (
              <Box>
                <Heading size="md" mb={3} color="green.600">
                  Active Now
                </Heading>
                <VStack align="stretch" gap={3}>
                  {activeEvents.map((event) => (
                    <Box
                      key={event.id}
                      bg="white"
                      borderRadius="lg"
                      boxShadow="md"
                      p={6}
                      borderColor="green.200"
                      borderWidth={2}
                    >
                      <Flex justify="space-between" align="start">
                        <VStack align="start" gap={2} flex={1}>
                          <HStack>
                            <Heading size="sm">
                              {event.title || "Untitled Event"}
                            </Heading>
                            <Badge colorPalette="green">Active</Badge>
                          </HStack>
                          <HStack fontSize="sm" color="gray.600">
                            <FaClock />
                            <Text>
                              {formatEventTime(
                                event.start_time,
                                event.end_time,
                              )}
                            </Text>
                          </HStack>
                          {event.description && (
                            <Text fontSize="sm" color="gray.700" noOfLines={2}>
                              {event.description}
                            </Text>
                          )}
                          {renderAttendees(event.attendees)}
                        </VStack>
                        <Link href={`/${roomName}`}>
                          <Button size="sm" colorPalette="green">
                            Join Room
                          </Button>
                        </Link>
                      </Flex>
                    </Box>
                  ))}
                </VStack>
              </Box>
            )}

            {/* Upcoming Events */}
            {upcomingEvents.length > 0 && (
              <Box>
                <Heading size="md" mb={3}>
                  Upcoming Events
                </Heading>
                <VStack align="stretch" spacing={3}>
                  {upcomingEvents.map((event) => (
                    <Card.Root key={event.id}>
                      <Card.Body>
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <Heading size="sm">
                              {event.title || "Untitled Event"}
                            </Heading>
                            {isEventUpcoming(event.start_time) && (
                              <Badge colorPalette="orange">Starting Soon</Badge>
                            )}
                          </HStack>
                          <HStack fontSize="sm" color="gray.600">
                            <FaClock />
                            <Text>
                              {formatEventTime(
                                event.start_time,
                                event.end_time,
                              )}
                            </Text>
                          </HStack>
                          {event.description && (
                            <Text fontSize="sm" color="gray.700" noOfLines={2}>
                              {event.description}
                            </Text>
                          )}
                          {renderAttendees(event.attendees)}
                        </VStack>
                      </Card.Body>
                    </Card.Root>
                  ))}
                </VStack>
              </Box>
            )}

            {/* Past Events */}
            {pastEvents.length > 0 && (
              <Box>
                <Heading size="md" mb={3} color="gray.500">
                  Past Events
                </Heading>
                <VStack align="stretch" spacing={3}>
                  {pastEvents.slice(0, 5).map((event) => (
                    <Card.Root key={event.id} opacity={0.7}>
                      <Card.Body>
                        <VStack align="start" spacing={2}>
                          <Heading size="sm">
                            {event.title || "Untitled Event"}
                          </Heading>
                          <HStack fontSize="sm" color="gray.600">
                            <FaClock />
                            <Text>
                              {formatEventTime(
                                event.start_time,
                                event.end_time,
                              )}
                            </Text>
                          </HStack>
                          {renderAttendees(event.attendees)}
                        </VStack>
                      </Card.Body>
                    </Card.Root>
                  ))}
                  {pastEvents.length > 5 && (
                    <Text fontSize="sm" color="gray.500" textAlign="center">
                      And {pastEvents.length - 5} more past events...
                    </Text>
                  )}
                </VStack>
              </Box>
            )}
          </VStack>
        )}
      </VStack>
    </Box>
  );
}
