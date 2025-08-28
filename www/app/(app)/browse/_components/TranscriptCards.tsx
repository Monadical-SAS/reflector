import React, { useState } from "react";
import {
  Box,
  Stack,
  Text,
  Flex,
  Link,
  Spinner,
  Badge,
  HStack,
  VStack,
} from "@chakra-ui/react";
import NextLink from "next/link";
import { formatTimeMs, formatLocalDate } from "../../../lib/time";
import TranscriptStatusIcon from "./TranscriptStatusIcon";
import TranscriptActionsMenu from "./TranscriptActionsMenu";
import {
  highlightMatches,
  generateTextFragment,
} from "../../../lib/textHighlight";
import { SearchResult } from "../../../lib/api-types";

interface TranscriptCardsProps {
  results: SearchResult[];
  query: string;
  isLoading?: boolean;
  onDelete: (transcriptId: string) => void;
  onReprocess: (transcriptId: string) => void;
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;

  const matches = highlightMatches(text, query);

  if (matches.length === 0) return text;

  // Sort matches by index to process them in order
  const sortedMatches = [...matches].sort((a, b) => a.index - b.index);

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  sortedMatches.forEach((match, i) => {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(
        <Text as="span" key={`text-${i}`} display="inline">
          {text.slice(lastIndex, match.index)}
        </Text>,
      );
    }

    // Add the highlighted match
    parts.push(
      <Text
        as="mark"
        key={`match-${i}`}
        bg="yellow.200"
        px={0.5}
        display="inline"
      >
        {match.match}
      </Text>,
    );

    lastIndex = match.index + match.match.length;
  });

  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(
      <Text as="span" key={`text-end`} display="inline">
        {text.slice(lastIndex)}
      </Text>,
    );
  }

  return parts;
}

const transcriptHref = (
  transcriptId: string,
  mainSnippet: string,
  query: string,
): `/transcripts/${string}` => {
  const urlTextFragment = mainSnippet
    ? generateTextFragment(mainSnippet, query)
    : null;
  const urlTextFragmentWithHash = urlTextFragment
    ? `#${urlTextFragment.k}=${encodeURIComponent(urlTextFragment.v)}`
    : "";
  return `/transcripts/${transcriptId}${urlTextFragmentWithHash}`;
};

// note that it's strongly tied to search logic - in case you want to use it independently, refactor
function TranscriptCard({
  result,
  query,
  onDelete,
  onReprocess,
}: {
  result: SearchResult;
  query: string;
  onDelete: (transcriptId: string) => void;
  onReprocess: (transcriptId: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const mainSnippet = result.search_snippets[0];
  const additionalSnippets = result.search_snippets.slice(1);
  const totalMatches = result.total_match_count || 0;
  const snippetsShown = result.search_snippets.length;
  const remainingMatches = totalMatches - snippetsShown;
  const hasAdditionalSnippets = additionalSnippets.length > 0;
  const resultTitle = result.title || "Unnamed Transcript";

  const formattedDuration = result.duration
    ? formatTimeMs(result.duration)
    : "N/A";
  const formattedDate = formatLocalDate(result.created_at);
  const source =
    result.source_kind === "room"
      ? result.room_name || result.room_id
      : result.source_kind;

  const handleExpandClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  return (
    <Box borderWidth={1} p={4} borderRadius="md" fontSize="sm">
      <Flex justify="space-between" alignItems="flex-start" gap="2">
        <Box>
          <TranscriptStatusIcon status={result.status} />
        </Box>
        <Box flex="1">
          {/* Title with highlighting and text fragment for deep linking */}
          <Link
            as={NextLink}
            href={transcriptHref(result.id, mainSnippet, query)}
            fontWeight="600"
            display="block"
            mb={2}
          >
            {highlightText(resultTitle, query)}
          </Link>

          {/* Metadata - Horizontal on desktop, vertical on mobile */}
          <Flex
            direction={{ base: "column", md: "row" }}
            gap={{ base: 1, md: 2 }}
            fontSize="xs"
            color="gray.600"
            flexWrap="wrap"
            align={{ base: "flex-start", md: "center" }}
          >
            <Flex align="center" gap={1}>
              <Text fontWeight="medium" color="gray.500">
                Source:
              </Text>
              <Text>{source}</Text>
            </Flex>
            <Text display={{ base: "none", md: "block" }} color="gray.400">
              •
            </Text>
            <Flex align="center" gap={1}>
              <Text fontWeight="medium" color="gray.500">
                Date:
              </Text>
              <Text>{formattedDate}</Text>
            </Flex>
            <Text display={{ base: "none", md: "block" }} color="gray.400">
              •
            </Text>
            <Flex align="center" gap={1}>
              <Text fontWeight="medium" color="gray.500">
                Duration:
              </Text>
              <Text>{formattedDuration}</Text>
            </Flex>
          </Flex>

          {/* Search Results Section - only show when searching */}
          {mainSnippet && (
            <>
              {/* Main Snippet */}
              <Box
                mt={3}
                p={2}
                bg="gray.50"
                borderLeft="2px solid"
                borderLeftColor="blue.400"
                borderRadius="sm"
                fontSize="xs"
              >
                <Text color="gray.700">
                  {highlightText(mainSnippet, query)}
                </Text>
              </Box>

              {hasAdditionalSnippets && (
                <>
                  <Flex
                    mt={2}
                    p={2}
                    bg="blue.50"
                    borderRadius="sm"
                    cursor="pointer"
                    onClick={handleExpandClick}
                    _hover={{ bg: "blue.100" }}
                    align="center"
                    justify="space-between"
                  >
                    <HStack gap={2}>
                      <Badge
                        bg="blue.500"
                        color="white"
                        fontSize="xs"
                        px={2}
                        borderRadius="full"
                      >
                        {remainingMatches > 0
                          ? `${additionalSnippets.length + remainingMatches}+`
                          : additionalSnippets.length}
                      </Badge>
                      <Text fontSize="xs" color="blue.600" fontWeight="medium">
                        more{" "}
                        {additionalSnippets.length + remainingMatches === 1
                          ? "match"
                          : "matches"}
                        {remainingMatches > 0 &&
                          ` (${additionalSnippets.length} shown)`}
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="blue.600">
                      {isExpanded ? "▲" : "▼"}
                    </Text>
                  </Flex>

                  {/* Additional Snippets */}
                  {isExpanded && (
                    <VStack align="stretch" gap={2} mt={2}>
                      {additionalSnippets.map((snippet, index) => (
                        <Box
                          key={index}
                          p={2}
                          bg="gray.50"
                          borderLeft="2px solid"
                          borderLeftColor="gray.300"
                          borderRadius="sm"
                          fontSize="xs"
                        >
                          <Text color="gray.700">
                            {highlightText(snippet, query)}
                          </Text>
                        </Box>
                      ))}
                    </VStack>
                  )}
                </>
              )}
            </>
          )}
        </Box>
        <TranscriptActionsMenu
          transcriptId={result.id}
          onDelete={onDelete}
          onReprocess={onReprocess}
        />
      </Flex>
    </Box>
  );
}

export default function TranscriptCards({
  results,
  query,
  isLoading,
  onDelete,
  onReprocess,
}: TranscriptCardsProps) {
  return (
    <Box position="relative">
      {isLoading && (
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
        opacity={isLoading ? 0.9 : 1}
        pointerEvents={isLoading ? "none" : "auto"}
        transition="opacity 0.2s ease-in-out"
      >
        <Stack gap={3}>
          {results.map((result) => (
            <TranscriptCard
              key={result.id}
              result={result}
              query={query}
              onDelete={onDelete}
              onReprocess={onReprocess}
            />
          ))}
        </Stack>
      </Box>
    </Box>
  );
}
