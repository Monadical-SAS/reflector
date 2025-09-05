import { Box, VStack, HStack, Text, Badge, Icon } from "@chakra-ui/react";
import { FaCalendarAlt, FaUsers, FaClock, FaInfoCircle } from "react-icons/fa";
import type { components } from "../reflector-api";

type Meeting = components["schemas"]["Meeting"];

interface MeetingInfoProps {
  meeting: Meeting;
  isOwner: boolean;
}

export default function MeetingInfo({ meeting, isOwner }: MeetingInfoProps) {
  const formatDuration = (start: string | Date, end: string | Date) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const now = new Date();

    // If meeting hasn't started yet
    if (startDate > now) {
      return `Scheduled for ${startDate.toLocaleTimeString()}`;
    }

    // Calculate duration
    const durationMs = now.getTime() - startDate.getTime();
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} minutes`;
  };

  const isCalendarMeeting = !!meeting.calendar_event_id;
  const metadata = meeting.calendar_metadata;

  return (
    <Box
      position="absolute"
      top="56px"
      right="8px"
      bg="white"
      borderRadius="md"
      boxShadow="lg"
      p={4}
      maxW="300px"
      zIndex={999}
    >
      <VStack align="stretch" gap={3}>
        {/* Meeting Title */}
        <HStack>
          <Icon
            as={isCalendarMeeting ? FaCalendarAlt : FaInfoCircle}
            color="blue.500"
          />
          <Text fontWeight="semibold" fontSize="md">
            {(metadata as any)?.title ||
              (isCalendarMeeting ? "Calendar Meeting" : "Unscheduled Meeting")}
          </Text>
        </HStack>

        {/* Meeting Status */}
        <HStack gap={2}>
          {meeting.is_active && (
            <Badge colorScheme="green" fontSize="xs">
              Active
            </Badge>
          )}
          {isCalendarMeeting && (
            <Badge colorScheme="blue" fontSize="xs">
              Calendar
            </Badge>
          )}
          {meeting.is_locked && (
            <Badge colorScheme="orange" fontSize="xs">
              Locked
            </Badge>
          )}
        </HStack>

        <Box h="1px" bg="gray.200" />

        {/* Meeting Details */}
        <VStack align="stretch" gap={2} fontSize="sm">
          {/* Participants */}
          <HStack>
            <Icon as={FaUsers} color="gray.500" />
            <Text>
              {meeting.num_clients}{" "}
              {meeting.num_clients === 1 ? "participant" : "participants"}
            </Text>
          </HStack>

          {/* Duration */}
          <HStack>
            <Icon as={FaClock} color="gray.500" />
            <Text>
              Duration: {formatDuration(meeting.start_date, meeting.end_date)}
            </Text>
          </HStack>

          {/* Calendar Description (Owner only) */}
          {isOwner && (metadata as any)?.description && (
            <>
              <Box h="1px" bg="gray.200" />
              <Box>
                <Text
                  fontWeight="semibold"
                  fontSize="xs"
                  color="gray.600"
                  mb={1}
                >
                  Description
                </Text>
                <Text fontSize="xs" color="gray.700">
                  {(metadata as any).description}
                </Text>
              </Box>
            </>
          )}

          {/* Attendees (Owner only) */}
          {isOwner &&
            (metadata as any)?.attendees &&
            (metadata as any).attendees.length > 0 && (
              <>
                <Box h="1px" bg="gray.200" />
                <Box>
                  <Text
                    fontWeight="semibold"
                    fontSize="xs"
                    color="gray.600"
                    mb={1}
                  >
                    Invited Attendees ({(metadata as any).attendees.length})
                  </Text>
                  <VStack align="stretch" gap={1}>
                    {(metadata as any).attendees
                      .slice(0, 5)
                      .map((attendee: any, idx: number) => (
                        <HStack key={idx} fontSize="xs">
                          <Badge
                            colorScheme={
                              attendee.status === "ACCEPTED"
                                ? "green"
                                : attendee.status === "DECLINED"
                                  ? "red"
                                  : attendee.status === "TENTATIVE"
                                    ? "yellow"
                                    : "gray"
                            }
                            fontSize="xs"
                            size="sm"
                          >
                            {attendee.status?.charAt(0) || "?"}
                          </Badge>
                          <Text color="gray.700" truncate>
                            {attendee.name || attendee.email}
                          </Text>
                        </HStack>
                      ))}
                    {(metadata as any).attendees.length > 5 && (
                      <Text fontSize="xs" color="gray.500" fontStyle="italic">
                        +{(metadata as any).attendees.length - 5} more
                      </Text>
                    )}
                  </VStack>
                </Box>
              </>
            )}

          {/* Recording Info */}
          {meeting.recording_type !== "none" && (
            <>
              <Box h="1px" bg="gray.200" />
              <HStack fontSize="xs">
                <Badge colorScheme="red" fontSize="xs">
                  Recording
                </Badge>
                <Text color="gray.600">
                  {meeting.recording_type === "cloud" ? "Cloud" : "Local"}
                  {meeting.recording_trigger !== "none" &&
                    ` (${meeting.recording_trigger})`}
                </Text>
              </HStack>
            </>
          )}
        </VStack>

        {/* Meeting Times */}
        <Box h="1px" bg="gray.200" />
        <VStack align="stretch" gap={1} fontSize="xs" color="gray.600">
          <Text>Start: {new Date(meeting.start_date).toLocaleString()}</Text>
          <Text>End: {new Date(meeting.end_date).toLocaleString()}</Text>
        </VStack>
      </VStack>
    </Box>
  );
}
