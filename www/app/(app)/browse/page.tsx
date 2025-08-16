"use client";
import React, { useState, useEffect } from "react";
import {
  Flex,
  Spinner,
  Heading,
  Text,
  Link,
  Box,
  Stack,
  Input,
  Button,
} from "@chakra-ui/react";
import { useSearchTranscripts } from "../transcripts/useSearchTranscripts";
import useSessionUser from "../../lib/useSessionUser";
import { Room, SourceKind, SearchResult } from "../../api";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import FilterSidebar from "./_components/FilterSidebar";
import Pagination from "./_components/Pagination";
import TranscriptCards from "./_components/TranscriptCards";
import DeleteTranscriptDialog from "./_components/DeleteTranscriptDialog";
import { formatLocalDate } from "../../lib/time";

export default function TranscriptBrowser() {
  // State for filters
  const [selectedSourceKind, setSelectedSourceKind] =
    useState<SourceKind | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState("");
  const [rooms, setRooms] = useState<Room[]>([]);

  // Search input state
  const [searchInputValue, setSearchInputValue] = useState("");
  const [searchStartTime, setSearchStartTime] = useState<number | undefined>();

  // Use the new search hook
  const {
    results,
    totalCount,
    isLoading,
    isValidating,
    error,
    hasMore,
    page,
    query,
    setPage,
    setQuery,
    setFilters,
    clearSearch,
  } = useSearchTranscripts(
    "",
    {
      roomIds: selectedRoomId ? [selectedRoomId] : undefined,
      sourceKind: selectedSourceKind,
    },
    {
      debounceMs: 0, // No debounce for button search
      pageSize: 20,
    },
  );

  const userName = useSessionUser().name;
  const [deletionLoading, setDeletionLoading] = useState(false);
  const api = useApi();
  const { setError } = useError();
  const cancelRef = React.useRef(null);
  const [transcriptToDeleteId, setTranscriptToDeleteId] =
    React.useState<string>();

  // Calculate search time
  const searchTime =
    searchStartTime && !isLoading ? Date.now() - searchStartTime : undefined;

  // Track search start time when loading starts
  useEffect(() => {
    if (isLoading && !searchStartTime) {
      setSearchStartTime(Date.now());
    } else if (!isLoading && searchStartTime) {
      // Keep the time until next search
    }
  }, [isLoading]);

  // Fetch rooms on mount
  useEffect(() => {
    if (!api) return;
    api
      .v1RoomsList({ page: 1 })
      .then((rooms) => setRooms(rooms.items))
      .catch((err) => setError(err, "There was an error fetching the rooms"));
  }, [api, setError]);

  // Handle filter changes
  const handleFilterTranscripts = (
    sourceKind: SourceKind | null,
    roomId: string,
  ) => {
    setSelectedSourceKind(sourceKind);
    setSelectedRoomId(roomId);
    setFilters({
      roomIds: roomId ? [roomId] : undefined,
      sourceKind: sourceKind,
    });
    setPage(0);
    // Clear search when filters change to show filtered results
    if (searchInputValue) {
      setSearchInputValue("");
      setQuery("");
    }
  };

  // Handle search button click
  const handleSearch = () => {
    setQuery(searchInputValue);
    // Keep filters active during search
    setPage(0);
    setSearchStartTime(undefined);
  };

  // Handle search on Enter key
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      handleSearch();
    }
  };

  // Delete transcript handlers
  const onCloseDeletion = () => setTranscriptToDeleteId(undefined);

  const confirmDeleteTranscript = (transcriptId: string) => {
    if (!api || deletionLoading) return;
    setDeletionLoading(true);
    api
      .v1TranscriptDelete({ transcriptId })
      .then(() => {
        setDeletionLoading(false);
        onCloseDeletion();
        // Refresh search results
        window.location.reload();
      })
      .catch((err) => {
        setDeletionLoading(false);
        setError(err, "There was an error deleting the transcript");
      });
  };

  const handleDeleteTranscript =
    (transcriptId: string) => (e: React.MouseEvent) => {
      e?.stopPropagation?.();
      setTranscriptToDeleteId(transcriptId);
    };

  const handleProcessTranscript =
    (transcriptId: string) => (e: React.MouseEvent) => {
      if (api) {
        api
          .v1TranscriptProcess({ transcriptId })
          .then((result) => {
            const status =
              result && typeof result === "object" && "status" in result
                ? (result as { status: string }).status
                : undefined;
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

  const transcriptToDelete = results?.find(
    (i) => i.id === transcriptToDeleteId,
  );
  const dialogTitle = transcriptToDelete?.title || "Unnamed Transcript";
  const dialogDate = transcriptToDelete?.created_at
    ? formatLocalDate(transcriptToDelete.created_at)
    : undefined;
  const dialogSource =
    transcriptToDelete?.source_kind === "room" && transcriptToDelete?.room_id
      ? transcriptToDelete.room_name || transcriptToDelete.room_id
      : transcriptToDelete?.source_kind;

  // Calculate pagination values (convert from offset-based to page-based)
  const pageSize = 20;
  const currentPage = Math.floor((page * pageSize) / pageSize) + 1;

  // Initial loading state - show spinner only on first load without query
  if (!query && isLoading && results.length === 0) {
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="100%"
      >
        <Spinner size="xl" />
      </Flex>
    );
  }

  return (
    <Flex
      flexDir="column"
      w={{ base: "full", md: "container.xl" }}
      mx="auto"
      pt={4}
    >
      <Flex
        flexDir="row"
        justifyContent="space-between"
        alignItems="center"
        mb={4}
      >
        <Heading size="lg">
          {userName ? `${userName}'s Transcriptions` : "Your Transcriptions"}{" "}
          {(isLoading || deletionLoading) && <Spinner size="sm" />}
        </Heading>
      </Flex>

      <Flex flexDir={{ base: "column", md: "row" }}>
        <FilterSidebar
          rooms={rooms}
          selectedSourceKind={selectedSourceKind}
          selectedRoomId={selectedRoomId}
          onFilterChange={handleFilterTranscripts}
        />

        <Flex
          flexDir="column"
          flex="1"
          pt={{ base: 4, md: 0 }}
          pb={4}
          gap={4}
          px={{ base: 0, md: 4 }}
        >
          {/* Search Bar - matching old style */}
          <Stack gap={2}>
            <Flex alignItems="center">
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

            {/* Show active filters */}
            {(selectedSourceKind || selectedRoomId) && (
              <Flex gap={2} flexWrap="wrap" align="center">
                <Text fontSize="sm" color="gray.600">
                  Active filters:
                </Text>
                {selectedSourceKind && (
                  <Box
                    px={2}
                    py={1}
                    bg="blue.100"
                    borderRadius="md"
                    fontSize="xs"
                  >
                    {selectedSourceKind === "room" && selectedRoomId
                      ? `Room: ${
                          rooms.find((r) => r.id === selectedRoomId)?.name ||
                          selectedRoomId
                        }`
                      : `Source: ${selectedSourceKind}`}
                  </Box>
                )}
                {query && (
                  <Box
                    px={2}
                    py={1}
                    bg="green.100"
                    borderRadius="md"
                    fontSize="xs"
                  >
                    Search: "{query}"
                  </Box>
                )}
              </Flex>
            )}
          </Stack>

          {/* Pagination at the top - matching old style */}
          <Pagination
            page={currentPage}
            setPage={(newPage) => setPage(newPage - 1)}
            total={totalCount}
            size={pageSize}
          />

          {/* Results Display - Always Cards */}
          <TranscriptCards
            results={results}
            query={query}
            isLoading={isLoading}
            onDelete={handleDeleteTranscript}
            onReprocess={handleProcessTranscript}
          />

          {/* Show no results message when needed */}
          {!isLoading && results.length === 0 && (
            <Flex
              flexDir="column"
              alignItems="center"
              justifyContent="center"
              py={8}
            >
              <Text textAlign="center">
                {query
                  ? `No results found for "${query}". Try adjusting your search terms.`
                  : "No transcripts found, but you can "}
                {!query && (
                  <>
                    <Link href="/transcripts/new" color="blue.500">
                      record a meeting
                    </Link>
                    {" to get started."}
                  </>
                )}
              </Text>
            </Flex>
          )}
        </Flex>
      </Flex>

      {/* Delete Dialog */}
      <DeleteTranscriptDialog
        isOpen={!!transcriptToDeleteId}
        onClose={onCloseDeletion}
        onConfirm={() =>
          transcriptToDeleteId && confirmDeleteTranscript(transcriptToDeleteId)
        }
        cancelRef={cancelRef}
        isLoading={deletionLoading}
        title={dialogTitle}
        date={dialogDate}
        source={dialogSource}
      />
    </Flex>
  );
}
