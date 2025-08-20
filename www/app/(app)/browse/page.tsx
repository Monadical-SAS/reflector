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
  IconButton,
} from "@chakra-ui/react";
import {
  useQueryState,
  parseAsString,
  parseAsInteger,
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
  FIRST_PAGE,
  PaginationPage,
  parsePaginationPage,
  totalPages as getTotalPages,
} from "./_components/Pagination";
import TranscriptCards from "./_components/TranscriptCards";
import DeleteTranscriptDialog from "./_components/DeleteTranscriptDialog";
import { formatLocalDate } from "../../lib/time";
import { RECORD_A_MEETING_URL } from "../../api/urls";

const SEARCH_FORM_QUERY_INPUT_NAME = "query" as const;

const usePrefetchRooms = (setRooms: (rooms: Room[]) => void): void => {
  const { setError } = useError();
  const api = useApi();
  useEffect(() => {
    if (!api) return;
    api
      .v1RoomsList({ page: 1 })
      .then((rooms) => setRooms(rooms.items))
      .catch((err) => setError(err, "There was an error fetching the rooms"));
  }, [api, setError]);
};

const SearchForm: React.FC<{
  setPage: (page: PaginationPage) => void;
  sourceKind: SourceKind | null;
  roomId: string | null;
  setSourceKind: (sourceKind: SourceKind | null) => void;
  setRoomId: (roomId: string | null) => void;
  rooms: Room[];
  searchQuery: string | null;
  setSearchQuery: (query: string | null) => void;
}> = ({
  setPage,
  sourceKind,
  roomId,
  setRoomId,
  setSourceKind,
  rooms,
  searchQuery,
  setSearchQuery,
}) => {
  // to keep the search input controllable + more fine grained control (urlSearchQuery is updated on submits)
  const [searchInputValue, setSearchInputValue] = useState(searchQuery || "");
  const handleSearchQuerySubmit = async (d: FormData) => {
    await setSearchQuery((d.get(SEARCH_FORM_QUERY_INPUT_NAME) as string) || "");
  };

  const handleClearSearch = () => {
    setSearchInputValue("");
    setSearchQuery(null);
    setPage(FIRST_PAGE);
  };
  return (
    <Stack gap={2}>
      <form action={handleSearchQuerySubmit}>
        <Flex alignItems="center">
          <Box position="relative" flex="1">
            <Input
              placeholder="Search transcriptions..."
              value={searchInputValue}
              onChange={(e) => setSearchInputValue(e.target.value)}
              name={SEARCH_FORM_QUERY_INPUT_NAME}
              pr={searchQuery ? "2.5rem" : undefined}
            />
            {searchQuery && (
              <IconButton
                aria-label="Clear search"
                size="sm"
                variant="ghost"
                onClick={handleClearSearch}
                position="absolute"
                right="0.25rem"
                top="50%"
                transform="translateY(-50%)"
                _hover={{ bg: "gray.100" }}
              >
                <LuX />
              </IconButton>
            )}
          </Box>
          <Button ml={2} type="submit">
            Search
          </Button>
        </Flex>
      </form>
      <UnderSearchFormFilterIndicators
        sourceKind={sourceKind}
        roomId={roomId}
        setSourceKind={setSourceKind}
        setRoomId={setRoomId}
        rooms={rooms}
      />
    </Stack>
  );
};

const UnderSearchFormFilterIndicators: React.FC<{
  sourceKind: SourceKind | null;
  roomId: string | null;
  setSourceKind: (sourceKind: SourceKind | null) => void;
  setRoomId: (roomId: string | null) => void;
  rooms: Room[];
}> = ({ sourceKind, roomId, setRoomId, setSourceKind, rooms }) => {
  return (
    <>
      {(sourceKind || roomId) && (
        <Flex gap={2} flexWrap="wrap" align="center">
          <Text fontSize="sm" color="gray.600">
            Active filters:
          </Text>
          {sourceKind && (
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
                {roomId
                  ? `Room: ${
                      rooms.find((r) => r.id === roomId)?.name || roomId
                    }`
                  : `Source: ${sourceKind}`}
              </Text>
              <Button
                size="xs"
                variant="ghost"
                minW="auto"
                h="auto"
                p="1px"
                onClick={() => {
                  setSourceKind(null);
                  // TODO questionable
                  setRoomId(null);
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
    </>
  );
};

const EmptyResult: React.FC<{
  searchQuery: string;
}> = ({ searchQuery }) => {
  return (
    <Flex flexDir="column" alignItems="center" justifyContent="center" py={8}>
      <Text textAlign="center">
        {searchQuery
          ? `No results found for "${searchQuery}". Try adjusting your search terms.`
          : "No transcripts found, but you can "}
        {!searchQuery && (
          <>
            <Link href={RECORD_A_MEETING_URL} color="blue.500">
              record a meeting
            </Link>
            {" to get started."}
          </>
        )}
      </Text>
    </Flex>
  );
};

export default function TranscriptBrowser() {
  const [urlSearchQuery, setUrlSearchQuery] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: false }),
  );

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

  const [urlPage, setPage] = useQueryState(
    "page",
    parseAsInteger.withDefault(1).withOptions({ shallow: false }),
  );

  const [page, _setSafePage] = useState(FIRST_PAGE);

  // safety net
  useEffect(() => {
    const maybePage = parsePaginationPage(urlPage);
    if ("error" in maybePage) {
      setPage(FIRST_PAGE).then(() => {
        /*may be called n times we dont care*/
      });
      return;
    }
    _setSafePage(maybePage.value);
  }, [urlPage]);

  const [rooms, setRooms] = useState<Room[]>([]);

  const pageSize = 20;
  const {
    results,
    totalCount: totalResults,
    isLoading,
    reload,
  } = useSearchTranscripts(
    urlSearchQuery,
    {
      roomIds: urlRoomId ? [urlRoomId] : null,
      sourceKind: urlSourceKind,
    },
    {
      pageSize,
      page,
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

  usePrefetchRooms(setRooms);

  const handleFilterTranscripts = (
    sourceKind: SourceKind | null,
    roomId: string,
  ) => {
    setUrlSourceKind(sourceKind);
    setUrlRoomId(roomId);
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
        reload();
      })
      .catch((err) => {
        setDeletionLoading(false);
        setError(err, "There was an error deleting the transcript");
      });
  };

  const handleProcessTranscript = (transcriptId: string) => {
    if (!api) {
      console.error("API not available on handleProcessTranscript");
      return;
    }
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
          <SearchForm
            setPage={setPage}
            sourceKind={urlSourceKind}
            roomId={urlRoomId}
            searchQuery={urlSearchQuery}
            setSearchQuery={setUrlSearchQuery}
            setSourceKind={setUrlSourceKind}
            setRoomId={setUrlRoomId}
            rooms={rooms}
          />

          {totalPages > 1 ? (
            <Pagination
              page={page}
              setPage={setPage}
              total={totalResults}
              size={pageSize}
            />
          ) : null}

          <TranscriptCards
            results={results}
            query={urlSearchQuery}
            isLoading={isLoading}
            onDelete={setTranscriptToDeleteId}
            onReprocess={handleProcessTranscript}
          />

          {!isLoading && results.length === 0 && (
            <EmptyResult searchQuery={urlSearchQuery} />
          )}
        </Flex>
      </Flex>

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
