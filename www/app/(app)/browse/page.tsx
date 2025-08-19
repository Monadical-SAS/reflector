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
import { useQueryState, parseAsString, parseAsInteger } from "nuqs";
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

// Custom parser for SourceKind
const parseAsSourceKind = parseAsString.withDefault("").withOptions({
  shallow: false,
});

// Validate SourceKind value
const validateSourceKind = (value: string): SourceKind | null => {
  if (value === "room" || value === "live" || value === "file") {
    return value as SourceKind;
  }
  return null;
};

export default function TranscriptBrowser() {
  // URL state management with nuqs
  // Query - only appears in URL after search is executed
  const [urlQuery, setUrlQuery] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: false }),
  );

  // Filters - immediately synced to URL
  const [urlSourceKind, setUrlSourceKind] = useQueryState(
    "source",
    parseAsSourceKind,
  );
  const [urlRoomId, setUrlRoomId] = useQueryState(
    "room",
    parseAsString.withDefault("").withOptions({ shallow: false }),
  );

  // Pagination - 1-based in URL, 0-based internally
  const [urlPage, setUrlPage] = useQueryState(
    "page",
    parseAsInteger.withDefault(1).withOptions({ shallow: false }),
  );

  // Local state for input field (separate from URL query)
  const [searchInputValue, setSearchInputValue] = useState("");

  // Rooms list
  const [rooms, setRooms] = useState<Room[]>([]);

  // Search timing
  const [searchStartTime, setSearchStartTime] = useState<number | undefined>();

  // Convert URL values to appropriate types
  const selectedSourceKind = validateSourceKind(urlSourceKind);
  const selectedRoomId = urlRoomId;
  const page = Math.max(0, (urlPage || 1) - 1); // Convert 1-based URL to 0-based internal

  // Use the search hook with URL state
  const {
    results,
    totalCount,
    isLoading,
    isValidating,
    error,
    hasMore,
    page: internalPage,
    query,
    setPage: setInternalPage,
    setQuery,
    setFilters,
    clearSearch,
  } = useSearchTranscripts(
    urlQuery, // Use URL query, not input value
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

  // Sync input value with URL query on mount and when URL query changes
  useEffect(() => {
    setSearchInputValue(urlQuery);
  }, [urlQuery]);

  // Sync internal page state with URL page
  useEffect(() => {
    setInternalPage(page);
  }, [page, setInternalPage]);

  // Fetch rooms on mount
  useEffect(() => {
    if (!api) return;
    api
      .v1RoomsList({ page: 1 })
      .then((rooms) => setRooms(rooms.items))
      .catch((err) => setError(err, "There was an error fetching the rooms"));
  }, [api, setError]);

  // Handle filter changes - update URL immediately
  const handleFilterTranscripts = (
    sourceKind: SourceKind | null,
    roomId: string,
  ) => {
    // Update URL state
    setUrlSourceKind(sourceKind || "");
    setUrlRoomId(roomId);
    setUrlPage(1); // Reset to page 1

    // If user has a search active, keep it
    // Otherwise clear the input field to match
    if (!urlQuery && searchInputValue) {
      setSearchInputValue("");
    }

    setSearchStartTime(undefined);
  };

  // Handle search button click - update URL
  const handleSearch = () => {
    if (searchInputValue !== urlQuery) {
      setUrlQuery(searchInputValue);
      setUrlPage(1); // Reset to page 1
      setSearchStartTime(undefined);
    }
  };

  // Handle clear search
  const handleClearSearch = () => {
    setSearchInputValue("");
    setUrlQuery("");
    setUrlPage(1);
    setSearchStartTime(undefined);
  };

  // Handle search on Enter key
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      handleSearch();
    }
  };

  // Handle page change - update URL
  const handlePageChange = (newPage: number) => {
    setUrlPage(newPage); // This is 1-based
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

  // Calculate pagination values
  const pageSize = 20;
  const currentPage = urlPage || 1; // 1-based for display

  // Initial loading state - show spinner only on first load without query
  if (!urlQuery && isLoading && results.length === 0) {
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
              {urlQuery && (
                <Button ml={2} variant="ghost" onClick={handleClearSearch}>
                  Clear
                </Button>
              )}
            </Flex>

            {/* Show active filters */}
            {(selectedSourceKind || selectedRoomId || urlQuery) && (
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
                {urlQuery && (
                  <Box
                    px={2}
                    py={1}
                    bg="green.100"
                    borderRadius="md"
                    fontSize="xs"
                  >
                    Search: "{urlQuery}"
                  </Box>
                )}
              </Flex>
            )}
          </Stack>

          {/* Pagination at the top - matching old style */}
          <Pagination
            page={currentPage}
            setPage={handlePageChange}
            total={totalCount}
            size={pageSize}
          />

          {/* Results Display - Always Cards */}
          <TranscriptCards
            results={results}
            query={urlQuery}
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
                {urlQuery
                  ? `No results found for "${urlQuery}". Try adjusting your search terms.`
                  : "No transcripts found, but you can "}
                {!urlQuery && (
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
