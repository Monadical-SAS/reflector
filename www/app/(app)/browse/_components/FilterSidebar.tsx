import React from "react";
import { Box, Stack, Link, Heading } from "@chakra-ui/react";
import NextLink from "next/link";
import { Room, SourceKind } from "../../../lib/api-types";

interface FilterSidebarProps {
  rooms: Room[];
  selectedSourceKind: SourceKind | null;
  selectedRoomId: string;
  onFilterChange: (sourceKind: SourceKind | null, roomId: string) => void;
}

// Type helper for source kind literals
const SK = {
  room: "room" as SourceKind,
  live: "live" as SourceKind,
  file: "file" as SourceKind,
};

export default function FilterSidebar({
  rooms,
  selectedSourceKind,
  selectedRoomId,
  onFilterChange,
}: FilterSidebarProps) {
  const myRooms = rooms.filter((room) => !room.is_shared);
  const sharedRooms = rooms.filter((room) => room.is_shared);

  return (
    <Box w={{ base: "full", md: "200px" }} p={4} bg="gray.100" rounded="md">
      <Stack gap={2}>
        <Link
          as={NextLink}
          fontSize="sm"
          href="#"
          onClick={() => onFilterChange(null, "")}
          color={selectedSourceKind === null ? "blue.500" : "gray.600"}
          fontWeight={selectedSourceKind === null ? "bold" : "normal"}
        >
          All Transcripts
        </Link>

        <Box borderBottomWidth="1px" my={2} />

        {myRooms.length > 0 && (
          <>
            <Heading size="sm">My Rooms</Heading>

            {myRooms.map((room) => (
              <Link
                key={room.id}
                as={NextLink}
                href="#"
                onClick={() => onFilterChange(SK.room, room.id)}
                color={
                  selectedSourceKind === SK.room && selectedRoomId === room.id
                    ? "blue.500"
                    : "gray.600"
                }
                fontWeight={
                  selectedSourceKind === SK.room && selectedRoomId === room.id
                    ? "bold"
                    : "normal"
                }
                fontSize="sm"
              >
                {room.name}
              </Link>
            ))}
          </>
        )}

        {sharedRooms.length > 0 && (
          <>
            <Heading size="sm">Shared Rooms</Heading>

            {sharedRooms.map((room) => (
              <Link
                key={room.id}
                as={NextLink}
                href="#"
                onClick={() => onFilterChange(SK.room, room.id)}
                color={
                  selectedSourceKind === SK.room && selectedRoomId === room.id
                    ? "blue.500"
                    : "gray.600"
                }
                fontWeight={
                  selectedSourceKind === SK.room && selectedRoomId === room.id
                    ? "bold"
                    : "normal"
                }
                fontSize="sm"
              >
                {room.name}
              </Link>
            ))}
          </>
        )}

        <Box borderBottomWidth="1px" my={2} />
        <Link
          as={NextLink}
          href="#"
          onClick={() => onFilterChange(SK.live, "")}
          color={selectedSourceKind === SK.live ? "blue.500" : "gray.600"}
          _hover={{ color: "blue.300" }}
          fontWeight={selectedSourceKind === SK.live ? "bold" : "normal"}
          fontSize="sm"
        >
          Live Transcripts
        </Link>
        <Link
          as={NextLink}
          href="#"
          onClick={() => onFilterChange(SK.file, "")}
          color={selectedSourceKind === SK.file ? "blue.500" : "gray.600"}
          _hover={{ color: "blue.300" }}
          fontWeight={selectedSourceKind === SK.file ? "bold" : "normal"}
          fontSize="sm"
        >
          Uploaded Files
        </Link>
      </Stack>
    </Box>
  );
}
