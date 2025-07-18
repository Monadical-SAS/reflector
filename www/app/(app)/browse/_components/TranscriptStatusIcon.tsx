import React from "react";
import { Icon, Tooltip } from "@chakra-ui/react";
import {
  FaCheck,
  FaTrash,
  FaStar,
  FaMicrophone,
  FaGear,
} from "react-icons/fa6";

interface TranscriptStatusIconProps {
  status: string;
}

export default function TranscriptStatusIcon({
  status,
}: TranscriptStatusIconProps) {
  switch (status) {
    case "ended":
      return (
        <Tooltip label="Processing done">
          <span>
            <Icon color="green" as={FaCheck} />
          </span>
        </Tooltip>
      );
    case "error":
      return (
        <Tooltip label="Processing error">
          <span>
            <Icon color="red.500" as={FaTrash} />
          </span>
        </Tooltip>
      );
    case "idle":
      return (
        <Tooltip label="New meeting, no recording">
          <span>
            <Icon color="yellow.500" as={FaStar} />
          </span>
        </Tooltip>
      );
    case "processing":
      return (
        <Tooltip label="Processing in progress">
          <span>
            <Icon color="gray.500" as={FaGear} />
          </span>
        </Tooltip>
      );
    case "recording":
      return (
        <Tooltip label="Recording in progress">
          <span>
            <Icon color="blue.500" as={FaMicrophone} />
          </span>
        </Tooltip>
      );
    default:
      return null;
  }
}
