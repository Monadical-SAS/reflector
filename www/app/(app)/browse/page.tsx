"use client";
import React, { useState, useEffect, FormEventHandler } from "react";
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
import {
  useQueryState,
  parseAsString,
  parseAsInteger,
  parseAsStringEnum,
  parseAsStringLiteral,
} from "nuqs";
import { LuX } from "react-icons/lu";
import { useSearchTranscripts } from "../transcripts/useSearchTranscripts";
import useSessionUser from "../../lib/useSessionUser";
import { Room, SourceKind, SearchResult, $SourceKind } from "../../api";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import FilterSidebar from "./_components/FilterSidebar";
import Pagination, {
  totalPages as getTotalPages,
} from "./_components/Pagination";
import TranscriptCards from "./_components/TranscriptCards";
import DeleteTranscriptDialog from "./_components/DeleteTranscriptDialog";
import { formatLocalDate } from "../../lib/time";
import { RECORD_A_MEETING_URL } from "../../api/urls";

const SEARCH_FORM_QUERY_INPUT_NAME = "query" as const;

export default function TranscriptBrowser() {
  const [urlSearchQuery, setUrlSearchQuery] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: false }),
  );

  // to keep the search input controllable + more fine grained control (urlSearchQuery is updated on submits)
  const [searchInputValue, setSearchInputValue] = useState("");

  const [urlSourceKind, setUrlSourceKind] = useQueryState(
    "source",
    parseAsStringLiteral($SourceKind.enum).withOptions({
      shallow: false,
    }),
  );
  const [urlRoomId, setUrlRoomId] = useQueryState(
    "room",
    parseAsString.withDefault("").withOptions({ shallow: false }),
  );

  const [page, setPage] = useQueryState(
    "page",
    parseAsInteger.withDefault(1).withOptions({ shallow: false }),
  );

  const [rooms, setRooms] = useState<Room[]>([]);

  const pageSize = 20;
  const {
    results,
    totalCount: totalResults,
    isLoading,
  } = useSearchTranscripts(
    urlSearchQuery, // Use URL query, not input value
    {
      roomIds: urlRoomId ? [urlRoomId] : undefined,
      sourceKind: urlSourceKind,
    },
    {
      pageSize,
    },
  );

  const totalPages = getTotalPages(totalResults, pageSize);

  const userName = useSessionUser().name;
  const [deletionLoading, setDeletionLoading] = useState(false);
  const api = useApi();
  const { setError } = useError();
  const cancelRef = React.useRef(null);
  const [transcriptToDeleteId, setTranscriptToDeleteId] =
    React.useState<string>();

  // Fetch rooms on mount
  useEffect(() => {
    if (!api) return;
    api
      .v1RoomsList({ page: 1 })
      .then((rooms) => setRooms(rooms.items))
      .catch((err) => setError(err, "There was an error fetching the rooms"));
  }, [api, setError]);

  const handleFilterTranscripts = (
    sourceKind: SourceKind | null,
    roomId: string,
  ) => {
    // Update URL state
    setUrlSourceKind(sourceKind);
    setUrlRoomId(roomId);
    setPage(1);
  };

  const handleSearchQuerySubmit = async (d: FormData) => {
    await setUrlSearchQuery(
      (d.get(SEARCH_FORM_QUERY_INPUT_NAME) as string) || "",
    );
  };

  const handleSearch = (searchInputValue: string) => {
    if (searchInputValue !== urlSearchQuery) {
      setUrlSearchQuery(searchInputValue);
      setPage(1);
    }
  };

  const handleClearSearch = () => {
    setSearchInputValue("");
    setUrlSearchQuery("");
    setPage(1);
  };

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

  if (isLoading && results.length === 0) {
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
          selectedSourceKind={urlSourceKind}
          selectedRoomId={urlRoomId}
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
          <Stack gap={2}>
            <form action={handleSearchQuerySubmit}>
              <Flex alignItems="center">
                <Input
                  placeholder="Search transcriptions..."
                  value={searchInputValue}
                  onChange={(e) => setSearchInputValue(e.target.value)}
                  name={SEARCH_FORM_QUERY_INPUT_NAME}
                />
                <Button ml={2} type="submit">
                  Search
                </Button>
                {urlSearchQuery && (
                  <Button ml={2} variant="ghost" onClick={handleClearSearch}>
                    Clear
                  </Button>
                )}
              </Flex>
            </form>

            {(urlSourceKind || urlRoomId) && (
              <Flex gap={2} flexWrap="wrap" align="center">
                <Text fontSize="sm" color="gray.600">
                  Active filters:
                </Text>
                {urlSourceKind && (
                  <Flex
                    align="center"
                    px={2}
                    py={1}
                    bg="blue.100"
                    borderRadius="md"
                    fontSize="xs"
                    gap={1}
                  >
                    <Text>
                      {urlRoomId
                        ? `Room: ${
                            rooms.find((r) => r.id === urlRoomId)?.name ||
                            urlRoomId
                          }`
                        : `Source: ${urlSourceKind}`}
                    </Text>
                    <Button
                      size="xs"
                      variant="ghost"
                      minW="auto"
                      h="auto"
                      p="1px"
                      onClick={() => {
                        setUrlSourceKind(null);
                        // TODO questionable
                        setUrlRoomId(null);
                      }}
                      _hover={{ bg: "blue.200" }}
                      aria-label="Clear filter"
                    >
                      <LuX size={14} />
                    </Button>
                  </Flex>
                )}
              </Flex>
            )}
          </Stack>

          {totalPages > 1 ? (
            <Pagination
              page={page}
              setPage={setPage}
              total={totalPages}
              size={pageSize}
            />
          ) : null}

          {/* Results Display - Always Cards */}
          <TranscriptCards
            results={results}
            query={urlSearchQuery}
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
                {urlSearchQuery
                  ? `No results found for "${urlSearchQuery}". Try adjusting your search terms.`
                  : "No transcripts found, but you can "}
                {!urlSearchQuery && (
                  <>
                    <Link href={RECORD_A_MEETING_URL} color="blue.500">
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
