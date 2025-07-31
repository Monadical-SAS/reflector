import { Text } from "@chakra-ui/react";
import { formatTime } from "../../../../lib/time";
import { generateHighContrastColor } from "../../../../lib/utils";

interface TopicSegmentProps {
  segment: {
    start: number;
    speaker: number;
    text: string;
  };
  speakerName: string;
}

export function TopicSegment({ segment, speakerName }: TopicSegmentProps) {
  return (
    <Text
      className="text-left text-slate-500 text-sm md:text-base"
      pb={2}
      lineHeight="1.3"
    >
      <Text as="span" color="gray.500" fontFamily="monospace" fontSize="sm">
        [{formatTime(segment.start)}]
      </Text>
      <Text
        as="span"
        fontWeight="bold"
        fontSize="sm"
        color={generateHighContrastColor(
          `Speaker ${segment.speaker}`,
          [96, 165, 250],
        )}
      >
        {" "}
        {speakerName}:
      </Text>{" "}
      <span>{segment.text}</span>
    </Text>
  );
}
