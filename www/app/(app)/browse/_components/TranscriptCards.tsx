import React from "react";
import { Box, Stack, Text, Flex, Link, Spinner } from "@chakra-ui/react";
import NextLink from "next/link";
import { GetTranscriptMinimal } from "../../../api";
import { formatTimeMs, formatLocalDate } from "../../../lib/time";
import TranscriptStatusIcon from "./TranscriptStatusIcon";
import TranscriptActionsMenu from "./TranscriptActionsMenu";

interface TranscriptCardsProps {
  transcripts: GetTranscriptMinimal[];
  onDelete: (transcriptId: string) => (e: any) => void;
  onReprocess: (transcriptId: string) => (e: any) => void;
  loading?: boolean;
}

export default function TranscriptCards({
  transcripts,
  onDelete,
  onReprocess,
  loading,
}: TranscriptCardsProps) {
  return (
    <Box display={{ base: "block", lg: "none" }} position="relative">
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
          <Spinner size="xl" color="gray.700" />
        </Flex>
      )}
      <Box
        opacity={loading ? 0.9 : 1}
        pointerEvents={loading ? "none" : "auto"}
        transition="opacity 0.2s ease-in-out"
      >
        <Stack gap={2}>
          {transcripts.map((item) => (
            <Box
              key={item.id}
              borderWidth={1}
              p={4}
              borderRadius="md"
              fontSize="sm"
            >
              <Flex justify="space-between" alignItems="flex-start" gap="2">
                <Box>
                  <TranscriptStatusIcon status={item.status} />
                </Box>
                <Box flex="1">
                  <Link
                    as={NextLink}
                    href={`/transcripts/${item.id}`}
                    fontWeight="600"
                    display="block"
                  >
                    {item.title || "Unnamed Transcript"}
                  </Link>
                  <Text>
                    Source:{" "}
                    {item.source_kind === "room"
                      ? item.room_name
                      : item.source_kind}
                  </Text>
                  <Text>Date: {formatLocalDate(item.created_at)}</Text>
                  <Text>Duration: {formatTimeMs(item.duration)}</Text>
                </Box>
                <TranscriptActionsMenu
                  transcriptId={item.id}
                  onDelete={onDelete}
                  onReprocess={onReprocess}
                />
              </Flex>
            </Box>
          ))}
        </Stack>
      </Box>
    </Box>
  );
}
