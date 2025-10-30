"use client";

import { Box, Button, Text, VStack, HStack } from "@chakra-ui/react";
import { CONSENT_DIALOG_TEXT } from "./constants";

interface ConsentDialogProps {
  onAccept: () => void;
  onReject: () => void;
}

export function ConsentDialog({ onAccept, onReject }: ConsentDialogProps) {
  return (
    <Box
      p={6}
      bg="rgba(255, 255, 255, 0.7)"
      borderRadius="lg"
      boxShadow="lg"
      maxW="md"
      mx="auto"
    >
      <VStack gap={4} alignItems="center">
        <Text fontSize="md" textAlign="center" fontWeight="medium">
          {CONSENT_DIALOG_TEXT.question}
        </Text>
        <HStack gap={4} justifyContent="center">
          <Button variant="ghost" size="sm" onClick={onReject}>
            {CONSENT_DIALOG_TEXT.rejectButton}
          </Button>
          <Button colorPalette="primary" size="sm" onClick={onAccept}>
            {CONSENT_DIALOG_TEXT.acceptButton}
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}
