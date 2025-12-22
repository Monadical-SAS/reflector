"use client";

import { Box, Text } from "@chakra-ui/react";
import { FaCircle } from "react-icons/fa6";
import {
  CONSENT_BUTTON_TOP_OFFSET,
  CONSENT_BUTTON_LEFT_OFFSET,
  CONSENT_BUTTON_Z_INDEX,
} from "./constants";

export function RecordingIndicator() {
  return (
    <Box
      position="absolute"
      top={CONSENT_BUTTON_TOP_OFFSET}
      left={CONSENT_BUTTON_LEFT_OFFSET}
      zIndex={CONSENT_BUTTON_Z_INDEX}
      display="flex"
      alignItems="center"
      gap={2}
      bg="red.500"
      color="white"
      px={3}
      py={1.5}
      borderRadius="md"
      fontSize="sm"
      fontWeight="medium"
    >
      <FaCircle size={8} />
      <Text>Recording</Text>
    </Box>
  );
}
