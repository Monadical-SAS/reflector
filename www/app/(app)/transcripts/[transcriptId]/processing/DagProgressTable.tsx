"use client";

import { useEffect, useState } from "react";
import { Table, Box, Icon, Spinner, Text, Badge } from "@chakra-ui/react";
import { FaCheck, FaXmark, FaClock, FaMinus } from "react-icons/fa6";
import type { DagTask, DagTaskStatus } from "../../useWebSockets";

function humanizeTaskName(name: string): string {
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function StatusIcon({ status }: { status: DagTaskStatus }) {
  switch (status) {
    case "completed":
      return (
        <Box as="span" title="Completed">
          <Icon color="green.500" as={FaCheck} />
        </Box>
      );
    case "running":
      return <Spinner size="sm" color="blue.500" />;
    case "failed":
      return (
        <Box as="span" title="Failed">
          <Icon color="red.500" as={FaXmark} />
        </Box>
      );
    case "queued":
      return (
        <Box as="span" title="Queued">
          <Icon color="gray.400" as={FaClock} />
        </Box>
      );
    case "cancelled":
      return (
        <Box as="span" title="Cancelled">
          <Icon color="gray.400" as={FaMinus} />
        </Box>
      );
    default:
      return null;
  }
}

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState<number>(() => {
    return (Date.now() - new Date(startedAt).getTime()) / 1000;
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - new Date(startedAt).getTime()) / 1000);
    }, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);

  return <Text fontSize="sm">{formatDuration(elapsed)}</Text>;
}

function DurationCell({ task }: { task: DagTask }) {
  if (task.status === "completed" && task.duration_seconds !== null) {
    return <Text fontSize="sm">{formatDuration(task.duration_seconds)}</Text>;
  }
  if (task.status === "running" && task.started_at) {
    return <ElapsedTimer startedAt={task.started_at} />;
  }
  return (
    <Text fontSize="sm" color="gray.400">
      --
    </Text>
  );
}

function ProgressCell({ task }: { task: DagTask }) {
  if (task.progress_pct === null && task.children_total === null) {
    return null;
  }

  return (
    <Box>
      {task.progress_pct !== null && (
        <Box
          w="100%"
          h="6px"
          bg="gray.200"
          borderRadius="full"
          overflow="hidden"
        >
          <Box
            h="100%"
            w={`${Math.min(100, Math.max(0, task.progress_pct))}%`}
            bg={task.status === "failed" ? "red.400" : "blue.400"}
            borderRadius="full"
            transition="width 0.3s ease"
          />
        </Box>
      )}
      {task.children_total !== null && (
        <Badge
          size="sm"
          colorPalette="gray"
          mt={task.progress_pct !== null ? 1 : 0}
        >
          {task.children_completed ?? 0}/{task.children_total}
        </Badge>
      )}
    </Box>
  );
}

function TaskRow({ task }: { task: DagTask }) {
  const [expanded, setExpanded] = useState(false);
  const hasFailed = task.status === "failed" && task.error;

  return (
    <>
      <Table.Row
        cursor={hasFailed ? "pointer" : "default"}
        onClick={hasFailed ? () => setExpanded((prev) => !prev) : undefined}
        _hover={hasFailed ? { bg: "gray.50" } : undefined}
      >
        <Table.Cell>
          <Text fontSize="sm" fontWeight="medium">
            {humanizeTaskName(task.name)}
          </Text>
        </Table.Cell>
        <Table.Cell>
          <StatusIcon status={task.status} />
        </Table.Cell>
        <Table.Cell>
          <DurationCell task={task} />
        </Table.Cell>
        <Table.Cell>
          <ProgressCell task={task} />
        </Table.Cell>
      </Table.Row>
      {hasFailed && expanded && (
        <Table.Row>
          <Table.Cell colSpan={4}>
            <Box bg="red.50" p={3} borderRadius="md">
              <Text fontSize="xs" color="red.700" whiteSpace="pre-wrap">
                {task.error}
              </Text>
            </Box>
          </Table.Cell>
        </Table.Row>
      )}
    </>
  );
}

export default function DagProgressTable({ tasks }: { tasks: DagTask[] }) {
  return (
    <Box w="100%" overflowX="auto">
      <Table.Root size="sm">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader fontWeight="600">Task</Table.ColumnHeader>
            <Table.ColumnHeader fontWeight="600" width="80px">
              Status
            </Table.ColumnHeader>
            <Table.ColumnHeader fontWeight="600" width="100px">
              Duration
            </Table.ColumnHeader>
            <Table.ColumnHeader fontWeight="600" width="140px">
              Progress
            </Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {tasks.map((task) => (
            <TaskRow key={task.name} task={task} />
          ))}
        </Table.Body>
      </Table.Root>
    </Box>
  );
}
