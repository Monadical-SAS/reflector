"use client";
import React, { useState, useEffect } from "react";
import {
  Flex,
  Spinner,
  Heading,
  Box,
  Text,
  Link,
  Stack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Divider,
  Input,
  Icon,
  Tooltip,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  Spacer,
} from "@chakra-ui/react";
import {
  FaCheck,
  FaTrash,
  FaStar,
  FaMicrophone,
  FaGear,
  FaEllipsisVertical,
  FaArrowRotateRight,
} from "react-icons/fa6";
import useTranscriptList from "../transcripts/useTranscriptList";
import useSessionUser from "../../lib/useSessionUser";
import NextLink from "next/link";
import { Room, GetTranscript } from "../../api";
import Pagination from "./pagination";
import { formatTimeMs } from "../../lib/time";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import { SourceKind } from "../../api";

export default function TranscriptBrowser() {
  const [selectedSourceKind, setSelectedSourceKind] =
    useState<SourceKind | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState("");
  const [rooms, setRooms] = useState<Room[]>([]);
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchInputValue, setSearchInputValue] = useState("");
  const { loading, response, refetch } = useTranscriptList(
    page,
    selectedSourceKind,
    selectedRoomId,
    searchTerm,
  );
  const userName = useSessionUser().name;
  const [deletionLoading, setDeletionLoading] = useState(false);
  const api = useApi();
  const { setError } = useError();
  const cancelRef = React.useRef(null);
  const [transcriptToDeleteId, setTranscriptToDeleteId] =
    React.useState<string>();
  const [deletedItemIds, setDeletedItemIds] = React.useState<string[]>();

  useEffect(() => {
    setDeletedItemIds([]);
  }, [page, response]);

  useEffect(() => {
    refetch();
  }, [selectedRoomId, page, searchTerm]);

  useEffect(() => {
    if (!api) return;
    api
      .v1RoomsList({ page: 1 })
      .then((rooms) => setRooms(rooms.items))
      .catch((err) => setError(err, "There was an error fetching the rooms"));
  }, [api]);

  const handleFilterTranscripts = (
    sourceKind: SourceKind | null,
    roomId: string,
  ) => {
    setSelectedSourceKind(sourceKind);
    setSelectedRoomId(roomId);
    setPage(1);
  };

  const handleSearch = () => {
    setPage(1);
    setSearchTerm(searchInputValue);
    setSelectedRoomId("");
    refetch();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      handleSearch();
    }
  };

  if (loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Spinner size="xl" />
      </Flex>
    );

  if (!loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Text>
          No transcripts found, but you can&nbsp;
          <Link href="/transcripts/new" className="underline">
            record a meeting
          </Link>
          &nbsp;to get started.
        </Text>
      </Flex>
    );

  const onCloseDeletion = () => setTranscriptToDeleteId(undefined);

  const handleDeleteTranscript = (transcriptId) => (e) => {
    e.stopPropagation();
    if (api && !deletionLoading) {
      setDeletionLoading(true);
      api
        .v1TranscriptDelete({ transcriptId })
        .then(() => {
          refetch();
          setDeletionLoading(false);
          onCloseDeletion();
          setDeletedItemIds((deletedItemIds) => [
            deletedItemIds,
            ...transcriptId,
          ]);
        })
        .catch((err) => {
          setDeletionLoading(false);
          setError(err, "There was an error deleting the transcript");
        });
    }
  };

  const handleProcessTranscript = (transcriptId) => (e) => {
    if (api) {
      api
        .v1TranscriptProcess({ transcriptId })
        .then((result) => {
          const status = (result as any).status;
          if (status === "already running") {
            setError(
              new Error("Processing is already running, please wait"),
              "Processing is already running, please wait",
            );
          }
        })
        .catch((err) => {
          setError(err, "There was an error processing the transcript");
        });
    }
  };

  return (
    <Flex
      flexDir="column"
      w={{ base: "full", md: "container.xl" }}
      mx="auto"
      p={4}
    >
      <Flex flexDir="row" justify="space-between" align="center" mb={4}>
        <Heading size="md">
          {userName ? `${userName}'s Transcriptions` : "Your Transcriptions"}{" "}
          {loading || (deletionLoading && <Spinner size="sm" />)}
        </Heading>
      </Flex>

      <Flex flexDir={{ base: "column", md: "row" }}>
        <Box w={{ base: "full", md: "300px" }} p={4} bg="gray.100">
          <Stack spacing={3}>
            <Link
              as={NextLink}
              href="#"
              onClick={() => handleFilterTranscripts(null, "")}
              color={selectedSourceKind === null ? "blue.500" : "gray.600"}
              _hover={{ color: "blue.300" }}
              fontWeight={selectedSourceKind === null ? "bold" : "normal"}
            >
              All Transcripts
            </Link>

            <Divider />

            {rooms.length > 0 && (
              <>
                <Heading size="sm" mb={2}>
                  My Rooms
                </Heading>

                {rooms.map((room) => (
                  <Link
                    key={room.id}
                    as={NextLink}
                    href="#"
                    onClick={() => handleFilterTranscripts("room", room.id)}
                    color={
                      selectedSourceKind === "room" &&
                      selectedRoomId === room.id
                        ? "blue.500"
                        : "gray.600"
                    }
                    _hover={{ color: "blue.300" }}
                    fontWeight={
                      selectedSourceKind === "room" &&
                      selectedRoomId === room.id
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
              onClick={() => handleFilterTranscripts("live", "")}
              color={selectedSourceKind === "live" ? "blue.500" : "gray.600"}
              _hover={{ color: "blue.300" }}
              fontWeight={selectedSourceKind === "live" ? "bold" : "normal"}
            >
              Live Transcripts
            </Link>
            <Link
              as={NextLink}
              href="#"
              onClick={() => handleFilterTranscripts("file", "")}
              color={selectedSourceKind === "file" ? "blue.500" : "gray.600"}
              _hover={{ color: "blue.300" }}
              fontWeight={selectedSourceKind === "file" ? "bold" : "normal"}
            >
              Uploaded Files
            </Link>
          </Stack>
        </Box>

        <Flex flexDir="column" flex="1" p={4} gap={4}>
          <Flex mb={4} alignItems="center">
            <Input
              placeholder="Search transcriptions..."
              value={searchInputValue}
              onChange={(e) => setSearchInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button ml={2} onClick={handleSearch}>
              Search
            </Button>
          </Flex>
          <Box display={{ base: "none", md: "block" }}>
            <Table colorScheme="gray">
              <Thead>
                <Tr>
                  <Th pl={12} width="400px">
                    Transcription Title
                  </Th>
                  <Th width="150px">Source</Th>
                  <Th width="200px">Date</Th>
                  <Th width="100px">Duration</Th>
                  <Th width="50px"></Th>
                </Tr>
              </Thead>
              <Tbody>
                {response?.items?.map((item: GetTranscript) => (
                  <Tr key={item.id}>
                    <Td>
                      <Flex alignItems="start">
                        {item.status === "ended" && (
                          <Tooltip label="Processing done">
                            <span>
                              <Icon color="green" as={FaCheck} />
                            </span>
                          </Tooltip>
                        )}
                        {item.status === "error" && (
                          <Tooltip label="Processing error">
                            <span>
                              <Icon color="red.500" as={FaTrash} />
                            </span>
                          </Tooltip>
                        )}
                        {item.status === "idle" && (
                          <Tooltip label="New meeting, no recording">
                            <span>
                              <Icon color="yellow.500" as={FaStar} />
                            </span>
                          </Tooltip>
                        )}
                        {item.status === "processing" && (
                          <Tooltip label="Processing in progress">
                            <span>
                              <Icon color="gray.500" as={FaGear} />
                            </span>
                          </Tooltip>
                        )}
                        {item.status === "recording" && (
                          <Tooltip label="Recording in progress">
                            <span>
                              <Icon color="blue.500" as={FaMicrophone} />
                            </span>
                          </Tooltip>
                        )}
                        <Link
                          as={NextLink}
                          href={`/transcripts/${item.id}`}
                          ml={2}
                        >
                          {item.title || "Unnamed Transcript"}
                        </Link>
                      </Flex>
                    </Td>
                    <Td>
                      {item.source_kind === "room"
                        ? item.room_name
                        : item.source_kind}
                    </Td>
                    <Td>
                      {new Date(item.created_at).toLocaleString("en-US", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                        hour: "numeric",
                        minute: "numeric",
                      })}
                    </Td>
                    <Td>{formatTimeMs(item.duration)}</Td>
                    <Td>
                      <Menu closeOnSelect={true}>
                        <MenuButton
                          as={IconButton}
                          icon={<Icon as={FaEllipsisVertical} />}
                          variant="outline"
                          aria-label="Options"
                        />
                        <MenuList>
                          <MenuItem onClick={handleDeleteTranscript(item.id)}>
                            Delete
                          </MenuItem>
                          <MenuItem onClick={handleProcessTranscript(item.id)}>
                            Reprocess
                          </MenuItem>
                        </MenuList>
                      </Menu>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
          <Box display={{ base: "block", md: "none" }}>
            <Stack spacing={2}>
              {response?.items?.map((item: GetTranscript) => (
                <Box key={item.id} borderWidth={1} p={4} borderRadius="md">
                  <Flex justify="space-between" alignItems="flex-start" gap="2">
                    <Box>
                      {item.status === "ended" && (
                        <Tooltip label="Processing done">
                          <span>
                            <Icon color="green" as={FaCheck} />
                          </span>
                        </Tooltip>
                      )}
                      {item.status === "error" && (
                        <Tooltip label="Processing error">
                          <span>
                            <Icon color="red.500" as={FaTrash} />
                          </span>
                        </Tooltip>
                      )}
                      {item.status === "idle" && (
                        <Tooltip label="New meeting, no recording">
                          <span>
                            <Icon color="yellow.500" as={FaStar} />
                          </span>
                        </Tooltip>
                      )}
                      {item.status === "processing" && (
                        <Tooltip label="Processing in progress">
                          <span>
                            <Icon color="gray.500" as={FaGear} />
                          </span>
                        </Tooltip>
                      )}
                      {item.status === "recording" && (
                        <Tooltip label="Recording in progress">
                          <span>
                            <Icon color="blue.500" as={FaMicrophone} />
                          </span>
                        </Tooltip>
                      )}
                    </Box>
                    <Box flex="1">
                      <Text fontWeight="bold">
                        {item.title || "Unnamed Transcript"}
                      </Text>
                      <Text>
                        Source:{" "}
                        {item.source_kind === "room"
                          ? item.room_name
                          : item.source_kind}
                      </Text>
                      <Text>
                        Date: {new Date(item.created_at).toLocaleString()}
                      </Text>
                      <Text>Duration: {formatTimeMs(item.duration)}</Text>
                    </Box>
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        icon={<Icon as={FaEllipsisVertical} />}
                        variant="outline"
                        aria-label="Options"
                      />
                      <MenuList>
                        <MenuItem onClick={handleDeleteTranscript(item.id)}>
                          Delete
                        </MenuItem>
                        <MenuItem onClick={handleProcessTranscript(item.id)}>
                          Reprocess
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Flex>
                </Box>
              ))}
            </Stack>
          </Box>
          <Pagination
            page={page}
            setPage={setPage}
            total={response?.total || 0}
            size={response?.items.length || 0}
          />
        </Flex>
      </Flex>

      <AlertDialog
        isOpen={!!transcriptToDeleteId}
        leastDestructiveRef={cancelRef}
        onClose={onCloseDeletion}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Transcript
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure? You can't undo this action afterwards.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onCloseDeletion}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDeleteTranscript(transcriptToDeleteId)}
                ml={3}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Flex>
  );
}
