import React from "react";
import { Button, Dialog, Text } from "@chakra-ui/react";

interface DeleteTranscriptDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  cancelRef: React.RefObject<any>;
  isLoading?: boolean;
  title?: string;
  date?: string;
  source?: string;
}

export default function DeleteTranscriptDialog({
  isOpen,
  onClose,
  onConfirm,
  cancelRef,
  isLoading,
  title,
  date,
  source,
}: DeleteTranscriptDialogProps) {
  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(e) => {
        if (!e.open) onClose();
      }}
      initialFocusEl={() => cancelRef.current}
    >
      <Dialog.Backdrop />
      <Dialog.Positioner>
        <Dialog.Content>
          <Dialog.Header fontSize="lg" fontWeight="bold">
            Delete transcript
          </Dialog.Header>
          <Dialog.Body>
            Are you sure you want to delete this transcript? This action cannot
            be undone.
            {title && (
              <Text mt={3} fontWeight="600">
                {title}
              </Text>
            )}
            {date && (
              <Text color="gray.600" fontSize="sm">
                Date: {date}
              </Text>
            )}
            {source && (
              <Text color="gray.600" fontSize="sm">
                Source: {source}
              </Text>
            )}
          </Dialog.Body>
          <Dialog.Footer>
            <Button
              ref={cancelRef as any}
              onClick={onClose}
              disabled={!!isLoading}
              variant="outline"
              colorPalette="gray"
            >
              Cancel
            </Button>
            <Button
              colorPalette="red"
              onClick={onConfirm}
              ml={3}
              disabled={!!isLoading}
            >
              Delete
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog.Positioner>
    </Dialog.Root>
  );
}
