import { useMemo } from "react";
import { Box, Heading, Text, VStack } from "@chakra-ui/react";
import type { components } from "../../../reflector-api";
import {
  useRoomsBulkMeetingStatus,
  BulkMeetingStatusMap,
} from "../../../lib/apiHooks";

type Room = components["schemas"]["Room"];
import { RoomTable } from "./RoomTable";
import { RoomCards } from "./RoomCards";
import { NonEmptyString } from "../../../lib/utils";

interface RoomListProps {
  title: string;
  rooms: Room[];
  linkCopied: string;
  onCopyUrl: (roomName: NonEmptyString) => void;
  onEdit: (roomId: string, roomData: any) => void;
  onDelete: (roomId: string) => void;
  emptyMessage?: string;
  mb?: number | string;
  pt?: number | string;
  loading?: boolean;
}

export function RoomList({
  title,
  rooms,
  linkCopied,
  onCopyUrl,
  onEdit,
  onDelete,
  emptyMessage = "No rooms found",
  mb,
  pt,
  loading,
}: RoomListProps) {
  const roomNames = useMemo(() => rooms.map((r) => r.name), [rooms]);
  const bulkStatusQuery = useRoomsBulkMeetingStatus(roomNames);
  const meetingStatusMap: BulkMeetingStatusMap = bulkStatusQuery.data ?? {};

  return (
    <VStack alignItems="start" gap={4} mb={mb} pt={pt}>
      <Heading size="md">{title}</Heading>
      {rooms.length > 0 ? (
        <Box w="full">
          <RoomTable
            rooms={rooms}
            linkCopied={linkCopied}
            onCopyUrl={onCopyUrl}
            onEdit={onEdit}
            onDelete={onDelete}
            loading={loading}
            meetingStatusMap={meetingStatusMap}
            meetingStatusLoading={bulkStatusQuery.isLoading}
          />
          <RoomCards
            rooms={rooms}
            linkCopied={linkCopied}
            onCopyUrl={onCopyUrl}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </Box>
      ) : (
        <Text>{emptyMessage}</Text>
      )}
    </VStack>
  );
}
