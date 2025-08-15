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
import { SearchResult } from "../../../api";
import { formatTimeMs, formatLocalDate } from "../../../lib/time";
import TranscriptStatusIcon from "./TranscriptStatusIcon";
import TranscriptActionsMenu from "./TranscriptActionsMenu";
import {
  highlightText as highlightTextUtil,
  generateTextFragment,
  renderHighlightedText,
} from "../../../lib/textHighlight";

interface TranscriptCardsProps {
  results: SearchResult[];
  query: string;
  isLoading?: boolean;
  onDelete: (transcriptId: string) => (e: any) => void;
  onReprocess: (transcriptId: string) => (e: any) => void;
}

interface ProcessedSnippet {
  text: string;
  rank?: number;
}

function processSnippets(snippets: string[]): ProcessedSnippet[] {
  return snippets.map((text, index) => ({
    text,
    rank: 1 - index * 0.1,
  }));
}

// Use the new highlighting utility that highlights individual words
function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;

  const highlighted = highlightTextUtil(text, query);

  // Convert <mark> tags to React components with Chakra UI styling
  const parts = highlighted.text.split(/(<mark>.*?<\/mark>)/g);

  return parts.map((part, index) => {
    if (part.startsWith("<mark>")) {
      const content = part.replace(/<\/?mark>/g, "");
      return (
        <Text as="mark" key={index} bg="yellow.200" px={0.5} display="inline">
          {content}
        </Text>
      );
    }
    return part;
  });
}

function TranscriptCard({
  result,
  query,
  onDelete,
  onReprocess,
}: {
  result: SearchResult;
  query: string;
  onDelete: (transcriptId: string) => (e: any) => void;
  onReprocess: (transcriptId: string) => (e: any) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const processedSnippets = processSnippets(result.search_snippets || []);
  const mainSnippet = processedSnippets[0];
  const additionalSnippets = processedSnippets.slice(1);
  const hasAdditionalSnippets = additionalSnippets.length > 0;
  const showSearchFeatures = query && query.length > 0;

  // Generate text fragment for deep linking to the first match
  const textFragment =
    showSearchFeatures && mainSnippet
      ? generateTextFragment(mainSnippet.text, query)
      : "";

  const relevancePercent = Math.round(result.rank * 100);
  const formattedDuration = result.duration
    ? formatTimeMs(result.duration * 1000)
    : "N/A";
  const formattedDate = formatLocalDate(result.created_at);
  const source =
    result.room_id ||
    ("source_kind" in result
      ? (result as SearchResult & { source_kind: string }).source_kind
      : "file");

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
            href={`/transcripts/${result.id}${textFragment}`}
            fontWeight="600"
            display="block"
            mb={2}
          >
            {showSearchFeatures
              ? highlightText(result.title || "Unnamed Transcript", query)
              : result.title || "Unnamed Transcript"}
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
              <Text>{source === "room" ? result.room_id : source}</Text>
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

          {/* Relevance score - only when searching and on desktop */}
          {showSearchFeatures && (
            <Box display={{ base: "none", md: "block" }}>
              <HStack gap={2} mt={2}>
                <Text fontSize="xs" color="gray.500">
                  Relevance:
                </Text>
                <Box
                  width="60px"
                  bg="gray.200"
                  height="4px"
                  borderRadius="full"
                >
                  <Box
                    bg={
                      relevancePercent >= 70
                        ? "green.500"
                        : relevancePercent >= 40
                        ? "yellow.500"
                        : "gray.500"
                    }
                    height="100%"
                    width={`${relevancePercent}%`}
                    borderRadius="full"
                  />
                </Box>
                <Text fontSize="xs" color="gray.600" fontWeight="medium">
                  {relevancePercent}%
                </Text>
              </HStack>
            </Box>
          )}

          {/* Search Results Section - only show when searching */}
          {showSearchFeatures && (
            <>
              {/* Main Snippet */}
              {mainSnippet && (
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
                    {highlightText(mainSnippet.text, query)}
                  </Text>
                </Box>
              )}

              {/* Additional Snippets Indicator */}
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
                        {additionalSnippets.length}
                      </Badge>
                      <Text fontSize="xs" color="blue.600" fontWeight="medium">
                        more{" "}
                        {additionalSnippets.length === 1 ? "match" : "matches"}
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
                          <Badge
                            bg="indigo.100"
                            color="indigo.800"
                            fontSize="xs"
                            mb={1}
                          >
                            Match {index + 2}
                          </Badge>
                          <Text color="gray.700">
                            {highlightText(snippet.text, query)}
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
