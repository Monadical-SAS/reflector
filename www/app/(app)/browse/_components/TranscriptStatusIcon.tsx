import React from "react";
import { Icon, Box } from "@chakra-ui/react";
import {
  FaCheck,
  FaTrash,
  FaStar,
  FaMicrophone,
  FaGear,
} from "react-icons/fa6";
import { TranscriptStatus } from "../../../lib/transcript";
import type { DagTask } from "../../../lib/UserEventsProvider";
import DagProgressDots from "./DagProgressDots";

interface TranscriptStatusIconProps {
  status: TranscriptStatus;
  dagStatus?: DagTask[] | null;
}

export default function TranscriptStatusIcon({
  status,
  dagStatus,
}: TranscriptStatusIconProps) {
  switch (status) {
    case "ended":
      return (
        <Box as="span" title="Processing done">
          <Icon color="green" as={FaCheck} />
        </Box>
      );
    case "error":
      return (
        <Box as="span" title="Processing error">
          <Icon color="red.500" as={FaTrash} />
        </Box>
      );
    case "idle":
      return (
        <Box as="span" title="New meeting, no recording">
          <Icon color="yellow.500" as={FaStar} />
        </Box>
      );
    case "processing":
      if (dagStatus && dagStatus.length > 0) {
        return <DagProgressDots tasks={dagStatus} />;
      }
      return (
        <Box as="span" title="Processing in progress">
          <Icon color="gray.500" as={FaGear} />
        </Box>
      );
    case "recording":
      return (
        <Box as="span" title="Recording in progress">
          <Icon color="blue.500" as={FaMicrophone} />
        </Box>
      );
    default:
      return null;
  }
}
