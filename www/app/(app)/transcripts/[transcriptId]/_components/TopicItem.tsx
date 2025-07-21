import { Box, Text, Accordion, Flex } from "@chakra-ui/react";
import { formatTime } from "../../../../lib/time";
import { Topic } from "../../webSocketTypes";
import { TopicSegment } from "./TopicSegment";

interface TopicItemProps {
  topic: Topic;
  isActive: boolean;
  getSpeakerName: (speakerNumber: number) => string | undefined;
}

export function TopicItem({ topic, isActive, getSpeakerName }: TopicItemProps) {
  return (
    <Accordion.Item value={topic.id} id={`topic-${topic.id}`}>
      <Accordion.ItemTrigger
        background={isActive ? "gray.50" : "white"}
        display="flex"
        alignItems="start"
        justifyContent="space-between"
      >
        <Flex
          display="flex"
          justifyContent="center"
          alignItems="center"
          height="24px"
          width="24px"
        >
          <Accordion.ItemIndicator />
        </Flex>
        <Box flex="1">{topic.title} </Box>
        <Text as="span" color="gray.500" fontSize="xs" pr={1}>
          {formatTime(topic.timestamp)}
        </Text>
      </Accordion.ItemTrigger>
      <Accordion.ItemContent>
        <Accordion.ItemBody p={4}>
          {isActive && (
            <>
              {topic.segments ? (
                <>
                  {topic.segments.map((segment, index: number) => (
                    <TopicSegment
                      key={index}
                      segment={segment}
                      speakerName={
                        getSpeakerName(segment.speaker) ||
                        `Speaker ${segment.speaker}`
                      }
                    />
                  ))}
                </>
              ) : (
                <>{topic.transcript}</>
              )}
            </>
          )}
        </Accordion.ItemBody>
      </Accordion.ItemContent>
    </Accordion.Item>
  );
}
