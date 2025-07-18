import React from "react";
import { Box, Stack, Link, Heading, Divider } from "@chakra-ui/react";
import NextLink from "next/link";
import { Room, SourceKind } from "../../../api";

interface FilterSidebarProps {
  rooms: Room[];
  selectedSourceKind: SourceKind | null;
  selectedRoomId: string;
  onFilterChange: (sourceKind: SourceKind | null, roomId: string) => void;
}

export default function FilterSidebar({
  rooms,
  selectedSourceKind,
  selectedRoomId,
  onFilterChange,
}: FilterSidebarProps) {
  const myRooms = rooms.filter((room) => !room.is_shared);
  const sharedRooms = rooms.filter((room) => room.is_shared);

  return (
    <Box w={{ base: "full", md: "300px" }} p={4} bg="gray.100">
      <Stack spacing={3}>
        <Link
          as={NextLink}
          href="#"
          onClick={() => onFilterChange(null, "")}
          color={selectedSourceKind === null ? "blue.500" : "gray.600"}
          _hover={{ color: "blue.300" }}
          fontWeight={selectedSourceKind === null ? "bold" : "normal"}
        >
          All Transcripts
        </Link>

        <Divider />

        {myRooms.length > 0 && (
          <>
            <Heading size="sm">My Rooms</Heading>

            {myRooms.map((room) => (
              <Link
                key={room.id}
                as={NextLink}
                href="#"
                onClick={() => onFilterChange("room", room.id)}
                color={
                  selectedSourceKind === "room" && selectedRoomId === room.id
                    ? "blue.500"
                    : "gray.600"
                }
                _hover={{ color: "blue.300" }}
                fontWeight={
                  selectedSourceKind === "room" && selectedRoomId === room.id
                    ? "bold"
                    : "normal"
                }
                ml={4}
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
                onClick={() => onFilterChange("room", room.id)}
                color={
                  selectedSourceKind === "room" && selectedRoomId === room.id
                    ? "blue.500"
                    : "gray.600"
                }
                _hover={{ color: "blue.300" }}
                fontWeight={
                  selectedSourceKind === "room" && selectedRoomId === room.id
                    ? "bold"
                    : "normal"
                }
                ml={4}
              >
                {room.name}
              </Link>
            ))}
          </>
        )}

        <Divider />
        <Link
          as={NextLink}
          href="#"
          onClick={() => onFilterChange("live", "")}
          color={selectedSourceKind === "live" ? "blue.500" : "gray.600"}
          _hover={{ color: "blue.300" }}
          fontWeight={selectedSourceKind === "live" ? "bold" : "normal"}
        >
          Live Transcripts
        </Link>
        <Link
          as={NextLink}
          href="#"
          onClick={() => onFilterChange("file", "")}
          color={selectedSourceKind === "file" ? "blue.500" : "gray.600"}
          _hover={{ color: "blue.300" }}
          fontWeight={selectedSourceKind === "file" ? "bold" : "normal"}
        >
          Uploaded Files
        </Link>
      </Stack>
    </Box>
  );
}
