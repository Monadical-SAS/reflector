import React from "react";
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Link,
  Flex,
  Spinner,
} from "@chakra-ui/react";
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
    <Box display={{ base: "none", md: "block" }} position="relative">
      {loading && (
        <Flex
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg="rgba(255, 255, 255, 0.8)"
          zIndex={10}
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
            {transcripts.map((item) => (
              <Tr key={item.id}>
                <Td>
                  <Flex alignItems="start">
                    <TranscriptStatusIcon status={item.status} />
                    <Link as={NextLink} href={`/transcripts/${item.id}`} ml={2}>
                      {item.title || "Unnamed Transcript"}
                    </Link>
                  </Flex>
                </Td>
                <Td>
                  {item.source_kind === "room"
                    ? item.room_name
                    : item.source_kind}
                </Td>
                <Td>{formatLocalDate(item.created_at)}</Td>
                <Td>{formatTimeMs(item.duration)}</Td>
                <Td>
                  <TranscriptActionsMenu
                    transcriptId={item.id}
                    onDelete={onDelete}
                    onReprocess={onReprocess}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
}
