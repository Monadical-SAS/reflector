import React from "react";
import { Box, Table, Link, Flex, Spinner } from "@chakra-ui/react";
import NextLink from "next/link";
import { GetTranscriptMinimal } from "../../../api";
import { formatTimeMs, formatLocalDate } from "../../../lib/time";
import TranscriptStatusIcon from "./TranscriptStatusIcon";
import TranscriptActionsMenu from "./TranscriptActionsMenu";

interface TranscriptTableProps {
  transcripts: GetTranscriptMinimal[];
  onDelete: (transcriptId: string) => (e: any) => void;
  onReprocess: (transcriptId: string) => (e: any) => void;
  loading?: boolean;
}

export default function TranscriptTable({
  transcripts,
  onDelete,
  onReprocess,
  loading,
}: TranscriptTableProps) {
  return (
    <Box display={{ base: "none", lg: "block" }} position="relative">
      {loading && (
        <Flex
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          align="center"
          justify="center"
        >
          <Spinner size="xl" color="gray.700" thickness="4px" />
        </Flex>
      )}
      <Box
        opacity={loading ? 0.9 : 1}
        pointerEvents={loading ? "none" : "auto"}
        transition="opacity 0.2s ease-in-out"
      >
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader
                width="16px"
                fontWeight="600"
              ></Table.ColumnHeader>
              <Table.ColumnHeader width="400px" fontWeight="600">
                Transcription Title
              </Table.ColumnHeader>
              <Table.ColumnHeader width="150px" fontWeight="600">
                Source
              </Table.ColumnHeader>
              <Table.ColumnHeader width="200px" fontWeight="600">
                Date
              </Table.ColumnHeader>
              <Table.ColumnHeader width="100px" fontWeight="600">
                Duration
              </Table.ColumnHeader>
              <Table.ColumnHeader
                width="50px"
                fontWeight="600"
              ></Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {transcripts.map((item) => (
              <Table.Row key={item.id}>
                <Table.Cell>
                  <TranscriptStatusIcon status={item.status} />
                </Table.Cell>
                <Table.Cell>
                  <Link as={NextLink} href={`/transcripts/${item.id}`}>
                    {item.title || "Unnamed Transcript"}
                  </Link>
                </Table.Cell>
                <Table.Cell>
                  {item.source_kind === "room"
                    ? item.room_name
                    : item.source_kind}
                </Table.Cell>
                <Table.Cell>{formatLocalDate(item.created_at)}</Table.Cell>
                <Table.Cell>{formatTimeMs(item.duration)}</Table.Cell>
                <Table.Cell>
                  <TranscriptActionsMenu
                    transcriptId={item.id}
                    onDelete={onDelete}
                    onReprocess={onReprocess}
                  />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Box>
    </Box>
  );
}
