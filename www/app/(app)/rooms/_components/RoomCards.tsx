import React from "react";
import {
  Box,
  Card,
  Flex,
  Heading,
  IconButton,
  Link,
  Spacer,
  Text,
  VStack,
  HStack,
} from "@chakra-ui/react";
import { FaLink } from "react-icons/fa6";
import { Room } from "../../../api";
import { RoomActionsMenu } from "./RoomActionsMenu";

interface RoomCardsProps {
  rooms: Room[];
  linkCopied: string;
  onCopyUrl: (roomName: string) => void;
  onEdit: (roomId: string, roomData: any) => void;
  onDelete: (roomId: string) => void;
}

const getRoomModeDisplay = (mode: string): string => {
  switch (mode) {
    case "normal":
      return "2-4 people";
    case "group":
      return "2-200 people";
    default:
      return mode;
  }
};

const getRecordingDisplay = (type: string, trigger: string): string => {
  if (type === "none") return "-";
  if (type === "local") return "Local";
  if (type === "cloud") {
    switch (trigger) {
      case "none":
        return "Cloud";
      case "prompt":
        return "Cloud (Prompt)";
      case "automatic-2nd-participant":
        return "Cloud (Auto)";
      default:
        return `Cloud`;
    }
  }
  return type;
};

export function RoomCards({
  rooms,
  linkCopied,
  onCopyUrl,
  onEdit,
  onDelete,
}: RoomCardsProps) {
  return (
    <Box display={{ base: "block", lg: "none" }}>
      <VStack gap={3} align="stretch">
        {rooms.map((room) => (
          <Card.Root key={room.id} size="sm">
            <Card.Body>
              <Flex alignItems="center" mt={-2}>
                <Heading size="sm">
                  <Link href={`/${room.name}`}>{room.name}</Link>
                </Heading>
                <Spacer />
                {linkCopied === room.name ? (
                  <Text color="green.500" mr={2} fontSize="sm">
                    Copied!
                  </Text>
                ) : (
                  <IconButton
                    aria-label="Copy URL"
                    onClick={() => onCopyUrl(room.name)}
                    mr={2}
                    size="sm"
                    variant="ghost"
                  >
                    <FaLink />
                  </IconButton>
                )}
                <RoomActionsMenu
                  roomId={room.id}
                  roomData={room}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              </Flex>
              <VStack align="start" fontSize="sm" gap={0}>
                {room.zulip_auto_post && (
                  <HStack gap={2}>
                    <Text fontWeight="500">Zulip:</Text>
                    <Text>
                      {room.zulip_stream && room.zulip_topic
                        ? `${room.zulip_stream} > ${room.zulip_topic}`
                        : room.zulip_stream || "Enabled"}
                    </Text>
                  </HStack>
                )}
                <HStack gap={2}>
                  <Text fontWeight="500">Size:</Text>
                  <Text>{getRoomModeDisplay(room.room_mode)}</Text>
                </HStack>
                <HStack gap={2}>
                  <Text fontWeight="500">Recording:</Text>
                  <Text>
                    {getRecordingDisplay(
                      room.recording_type,
                      room.recording_trigger,
                    )}
                  </Text>
                </HStack>
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </Box>
  );
}
