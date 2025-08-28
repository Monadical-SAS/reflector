import { Box, Heading, Text, VStack } from "@chakra-ui/react";
import { Room } from "../../../lib/api-types";
import { RoomTable } from "./RoomTable";
import { RoomCards } from "./RoomCards";

interface RoomListProps {
  title: string;
  rooms: Room[];
  linkCopied: string;
  onCopyUrl: (roomName: string) => void;
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
