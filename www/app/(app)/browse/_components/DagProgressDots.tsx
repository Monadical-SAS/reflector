import React from "react";
import { Box, Flex } from "@chakra-ui/react";
import type { DagTask } from "../../../lib/UserEventsProvider";

const pulseKeyframes = `
  @keyframes dagDotPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
`;

function humanizeTaskName(name: string): string {
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function dotProps(status: DagTask["status"]): Record<string, unknown> {
  switch (status) {
    case "completed":
      return { bg: "green.500" };
    case "running":
      return {
        bg: "blue.500",
        style: { animation: "dagDotPulse 1.5s ease-in-out infinite" },
      };
    case "failed":
      return { bg: "red.500" };
    case "cancelled":
      return { bg: "gray.400" };
    case "queued":
    default:
      return {
        bg: "transparent",
        border: "1px solid",
        borderColor: "gray.400",
      };
  }
}

export default function DagProgressDots({ tasks }: { tasks: DagTask[] }) {
  return (
    <>
      <style>{pulseKeyframes}</style>
      <Flex gap="2px" alignItems="center" flexWrap="wrap">
        {tasks.map((task) => (
          <Box
            key={task.name}
            w="4px"
            h="4px"
            borderRadius="full"
            flexShrink={0}
            title={humanizeTaskName(task.name)}
            {...dotProps(task.status)}
          />
        ))}
      </Flex>
    </>
  );
}
