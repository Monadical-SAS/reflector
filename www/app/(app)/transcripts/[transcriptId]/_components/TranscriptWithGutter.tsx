import { Box, Text, IconButton } from "@chakra-ui/react";
import { ChevronUp } from "lucide-react";
import { Topic } from "../../webSocketTypes";
import { getTopicColor } from "../../../../lib/topicColors";
import { TOPICS_SCROLL_DIV_ID } from "./constants";

interface TranscriptWithGutterProps {
  topics: Topic[];
  getSpeakerName: (speakerNumber: number) => string | undefined;
  onGutterClick: (topicId: string) => void;
}

export function TranscriptWithGutter({
  topics,
  getSpeakerName,
  onGutterClick,
}: TranscriptWithGutterProps) {
  const scrollToTopics = () => {
    // Scroll to the topic list at the top
    const topicList = document.getElementById(TOPICS_SCROLL_DIV_ID);
    if (topicList) {
      topicList.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };

  return (
    <Box>
      {topics.map((topic, topicIndex) => {
        const color = getTopicColor(topicIndex);

        return (
          <Box key={topic.id} position="relative">
            {/* Topic Header with Up Button */}
            <Box
              py={3}
              px={4}
              fontWeight="semibold"
              fontSize="lg"
              display="flex"
              alignItems="center"
              justifyContent="space-between"
            >
              <Text>{topic.title}</Text>
              <IconButton
                aria-label="Scroll to topics"
                size="sm"
                variant="ghost"
                onClick={scrollToTopics}
              >
                <ChevronUp size={16} />
              </IconButton>
            </Box>

            {/* Segments container with single gutter */}
            <Box position="relative">
              {/* Single continuous gutter for entire topic */}
              <Box
                className="topic-gutter"
                position="absolute"
                left={0}
                top={0}
                bottom={0}
                width="4px"
                bg={color}
                cursor="pointer"
                transition="all 0.2s"
                _hover={{
                  filter: "brightness(1.2)",
                  width: "6px",
                }}
                onClick={() => onGutterClick(topic.id)}
              />

              {/* Segments */}
              {topic.segments?.map((segment, segmentIndex) => (
                <Box
                  key={segmentIndex}
                  id={`segment-${topic.id}-${segmentIndex}`}
                  py={2}
                  px={4}
                  pl={12}
                  _hover={{
                    bg: "gray.50",
                  }}
                >
                  {/* Segment Content */}
                  <Text fontSize="sm">
                    <Text as="span" fontWeight="semibold" color="gray.700">
                      {getSpeakerName(segment.speaker) ||
                        `Speaker ${segment.speaker}`}
                      :
                    </Text>{" "}
                    {segment.text}
                  </Text>
                </Box>
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
