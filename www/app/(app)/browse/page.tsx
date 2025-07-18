"use client";
import React, { useState, useEffect } from "react";
import { Flex, Spinner, Heading, Text, Link } from "@chakra-ui/react";
import useTranscriptList from "../transcripts/useTranscriptList";
import useSessionUser from "../../lib/useSessionUser";
import { Room } from "../../api";
import Pagination from "./_components/Pagination";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import { SourceKind } from "../../api";
import FilterSidebar from "./_components/FilterSidebar";
import SearchBar from "./_components/SearchBar";
import TranscriptTable from "./_components/TranscriptTable";
import TranscriptCards from "./_components/TranscriptCards";
import DeleteTranscriptDialog from "./_components/DeleteTranscriptDialog";

export default function TranscriptBrowser() {
  const [selectedSourceKind, setSelectedSourceKind] =
    useState<SourceKind | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState("");
  const [rooms, setRooms] = useState<Room[]>([]);
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
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

  const handleSearch = (searchTerm: string) => {
    setPage(1);
    setSearchTerm(searchTerm);
    setSelectedSourceKind(null);
    setSelectedRoomId("");
  };

  if (loading && !response)
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

  if (!loading && !response)
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="100%"
      >
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
      <Flex
        flexDir="row"
        justifyContent="space-between"
        alignItems="center"
        mb={4}
      >
        <Heading size="lg">
          {userName ? `${userName}'s Transcriptions` : "Your Transcriptions"}{" "}
          {loading || (deletionLoading && <Spinner size="sm" />)}
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
          <SearchBar onSearch={handleSearch} />
          <Pagination
            page={page}
            setPage={setPage}
            total={response?.total || 0}
            size={response?.size || 0}
          />
          <TranscriptTable
            transcripts={response?.items || []}
            onDelete={handleDeleteTranscript}
            onReprocess={handleProcessTranscript}
            loading={loading}
          />
          <TranscriptCards
            transcripts={response?.items || []}
            onDelete={handleDeleteTranscript}
            onReprocess={handleProcessTranscript}
            loading={loading}
          />
        </Flex>
      </Flex>

      <DeleteTranscriptDialog
        open={!!transcriptToDeleteId}
        onClose={onCloseDeletion}
        onConfirm={() => handleDeleteTranscript(transcriptToDeleteId)(null)}
        cancelRef={cancelRef}
      />
    </Flex>
  );
}
