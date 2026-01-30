import React, { useState, useEffect } from "react";
import ScrollToBottom from "../../scrollToBottom";
import { Topic } from "../../webSocketTypes";
import { Box, Flex, Text } from "@chakra-ui/react";
import { formatTime } from "../../../../lib/time";
import { getTopicColor } from "../../../../lib/topicColors";
import { TranscriptStatus } from "../../../../lib/transcript";
import { featureEnabled } from "../../../../lib/features";
import { TOPICS_SCROLL_DIV_ID } from "./constants";

type TopicListProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  autoscroll: boolean;
  transcriptId: string;
  status: TranscriptStatus | null;
  currentTranscriptText: any;
  onTopicClick?: (topicId: string) => void;
};

export function TopicList({
  topics,
  useActiveTopic,
  autoscroll,
  transcriptId,
  status,
  currentTranscriptText,
  onTopicClick,
}: TopicListProps) {
  const [activeTopic, setActiveTopic] = useActiveTopic;
  const [hoveredTopicId, setHoveredTopicId] = useState<string | null>(null);
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);

  const toggleScroll = (element: HTMLElement) => {
    const bottom =
      Math.abs(
        element.scrollHeight - element.clientHeight - element.scrollTop,
      ) < 2 || element.scrollHeight == element.clientHeight;
    if (!bottom && autoscrollEnabled) {
      setAutoscrollEnabled(false);
    } else if (bottom && !autoscrollEnabled) {
      setAutoscrollEnabled(true);
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    toggleScroll(e.target as HTMLElement);
  };

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById(TOPICS_SCROLL_DIV_ID);
    if (topicsDiv) topicsDiv.scrollTop = topicsDiv.scrollHeight;
  };

  useEffect(() => {
    if (autoscroll) {
      const topicsDiv = document.getElementById(TOPICS_SCROLL_DIV_ID);
      topicsDiv && toggleScroll(topicsDiv);
    }
  }, [activeTopic, autoscroll]);

  useEffect(() => {
    if (autoscroll && autoscrollEnabled) scrollToBottom();
  }, [topics.length, currentTranscriptText]);

  useEffect(() => {
    if (autoscroll) {
      setActiveTopic(topics[topics.length - 1]);
    }
  }, [topics, autoscroll]);

  const handleTopicClick = (topic: Topic) => {
    setActiveTopic(topic);
    if (onTopicClick) {
      onTopicClick(topic.id);
    }
  };

  const handleTopicMouseEnter = (topic: Topic) => {
    setHoveredTopicId(topic.id);
    // If already active, toggle off when mousing over
    if (activeTopic?.id === topic.id) {
      setActiveTopic(null);
    } else {
      setActiveTopic(topic);
    }
  };

  const handleTopicMouseLeave = () => {
    setHoveredTopicId(null);
  };

  const requireLogin = featureEnabled("requireLogin");

  return (
    <Flex
      position="relative"
      w="full"
      h="200px"
      flexDirection="column"
      flexShrink={0}
    >
      {autoscroll && (
        <ScrollToBottom
          visible={!autoscrollEnabled}
          handleScrollBottom={scrollToBottom}
        />
      )}

      <Box
        id={TOPICS_SCROLL_DIV_ID}
        overflowY="auto"
        h="full"
        onScroll={handleScroll}
        width="full"
      >
        {topics.length > 0 && (
          <Flex direction="column" gap={1} p={2}>
            {topics.map((topic, index) => {
              const color = getTopicColor(index);
              const isActive = activeTopic?.id === topic.id;
              const isHovered = hoveredTopicId === topic.id;

              return (
                <Flex
                  key={topic.id}
                  id={`topic-${topic.id}`}
                  gap={2}
                  align="center"
                  py={1}
                  px={2}
                  cursor="pointer"
                  bg={isActive || isHovered ? "gray.100" : "transparent"}
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleTopicClick(topic)}
                  onMouseEnter={() => handleTopicMouseEnter(topic)}
                  onMouseLeave={handleTopicMouseLeave}
                >
                  {/* Color indicator */}
                  <Box
                    w="12px"
                    h="12px"
                    borderRadius="full"
                    bg={color}
                    flexShrink={0}
                  />

                  {/* Topic title */}
                  <Text
                    flex={1}
                    fontSize="sm"
                    fontWeight={isActive ? "semibold" : "normal"}
                  >
                    {topic.title}
                  </Text>

                  {/* Timestamp */}
                  <Text as="span" color="gray.500" fontSize="xs" flexShrink={0}>
                    {formatTime(topic.timestamp)}
                  </Text>
                </Flex>
              );
            })}
          </Flex>
        )}

        {status == "recording" && (
          <Box textAlign="center">
            <Text>{currentTranscriptText}</Text>
          </Box>
        )}
        {(status == "recording" || status == "idle") &&
          currentTranscriptText.length == 0 &&
          topics.length == 0 && (
            <Box textAlign="center" color="gray">
              <Text>
                Full discussion transcript will appear here after you start
                recording.
              </Text>
              <Text>
                It may take up to 5 minutes of conversation to first appear.
              </Text>
            </Box>
          )}
        {status == "processing" && (
          <Box textAlign="center" color="gray">
            <Text>We are processing the recording, please wait.</Text>
            {!requireLogin && (
              <span>
                Please do not navigate away from the page during this time.
              </span>
            )}
          </Box>
        )}
        {status == "ended" && topics.length == 0 && (
          <Box textAlign="center" color="gray">
            <Text>Recording has ended without topics being found.</Text>
          </Box>
        )}
        {status == "error" && (
          <Box textAlign="center" color="gray">
            <Text>There was an error processing your recording</Text>
          </Box>
        )}
      </Box>
    </Flex>
  );
}
