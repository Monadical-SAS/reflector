import { Box, Text, Accordion } from "@chakra-ui/react";
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
        alignItems="center"
        justifyContent="space-between"
      >
        <Accordion.ItemIndicator />
        <Box flex="1" lineHeight="1.1">
          {topic.title}{" "}
          <Text as="span" color="gray.500" fontSize="sm" fontWeight="bold">
            &nbsp;[{formatTime(topic.timestamp)}]&nbsp;-&nbsp;[
            {formatTime(topic.timestamp + (topic.duration || 0))}]
          </Text>
        </Box>
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
