import React from "react";
import {
  Box,
  Table,
  Link,
  Flex,
  IconButton,
  Text,
  Spinner,
  Badge,
} from "@chakra-ui/react";
import { LuLink } from "react-icons/lu";
import type { components } from "../../../reflector-api";

type Room = components["schemas"]["Room"];
import { RoomActionsMenu } from "./RoomActionsMenu";
import {
  getPlatformDisplayName,
  getPlatformColor,
} from "../../../lib/videoPlatforms";

interface RoomTableProps {
  rooms: Room[];
  linkCopied: string;
  onCopyUrl: (roomName: string) => void;
  onEdit: (roomId: string, roomData: any) => void;
  onDelete: (roomId: string) => void;
  loading?: boolean;
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
        return "Cloud (None)";
      case "prompt":
        return "Cloud (Prompt)";
      case "automatic-2nd-participant":
        return "Cloud (Auto)";
      default:
        return `Cloud (${trigger})`;
    }
  }
  return type;
};

const getZulipDisplay = (
  autoPost: boolean,
  stream: string,
  topic: string,
): string => {
  if (!autoPost) return "-";
  if (stream && topic) return `${stream} > ${topic}`;
  if (stream) return stream;
  return "Enabled";
};

export function RoomTable({
  rooms,
  linkCopied,
  onCopyUrl,
  onEdit,
  onDelete,
  loading,
}: RoomTableProps) {
  return (
    <Box display={{ base: "none", lg: "block" }} position="relative">
      {loading && (
        <Flex
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          align="center"
          justify="center"
        >
          <Spinner size="xl" color="gray.700" />
        </Flex>
      )}
      <Box
        opacity={loading ? 0.9 : 1}
        pointerEvents={loading ? "none" : "auto"}
        transition="opacity 0.2s ease-in-out"
      >
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader width="200px" fontWeight="600">
                Room Name
              </Table.ColumnHeader>
              <Table.ColumnHeader width="120px" fontWeight="600">
                Platform
              </Table.ColumnHeader>
              <Table.ColumnHeader width="200px" fontWeight="600">
                Zulip
              </Table.ColumnHeader>
              <Table.ColumnHeader width="130px" fontWeight="600">
                Room Size
              </Table.ColumnHeader>
              <Table.ColumnHeader width="180px" fontWeight="600">
                Recording
              </Table.ColumnHeader>
              <Table.ColumnHeader
                width="100px"
                fontWeight="600"
              ></Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {rooms.map((room) => (
              <Table.Row key={room.id}>
                <Table.Cell>
                  <Link href={`/${room.name}`}>{room.name}</Link>
                </Table.Cell>
                <Table.Cell>
                  <Badge
                    colorPalette={getPlatformColor(room.platform)}
                    size="sm"
                  >
                    {getPlatformDisplayName(room.platform)}
                  </Badge>
                </Table.Cell>
                <Table.Cell>
                  {getZulipDisplay(
                    room.zulip_auto_post,
                    room.zulip_stream,
                    room.zulip_topic,
                  )}
                </Table.Cell>
                <Table.Cell>{getRoomModeDisplay(room.room_mode)}</Table.Cell>
                <Table.Cell>
                  {getRecordingDisplay(
                    room.recording_type,
                    room.recording_trigger,
                  )}
                </Table.Cell>
                <Table.Cell>
                  <Flex alignItems="center" gap={2}>
                    {linkCopied === room.name ? (
                      <Text color="green.500" fontSize="sm">
                        Copied!
                      </Text>
                    ) : (
                      <IconButton
                        aria-label="Copy URL"
                        onClick={() => onCopyUrl(room.name)}
                        size="sm"
                        variant="ghost"
                      >
                        <LuLink />
                      </IconButton>
                    )}
                    <RoomActionsMenu
                      roomId={room.id}
                      roomData={room}
                      onEdit={onEdit}
                      onDelete={onDelete}
                    />
                  </Flex>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Box>
    </Box>
  );
}
