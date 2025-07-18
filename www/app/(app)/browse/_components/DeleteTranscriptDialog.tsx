import React from "react";
import { Button } from "@chakra-ui/react";
// import { Dialog } from "@chakra-ui/react";

interface DeleteTranscriptDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  cancelRef: React.RefObject<any>;
}

export default function DeleteTranscriptDialog({
  isOpen,
  onClose,
  onConfirm,
  cancelRef,
}: DeleteTranscriptDialogProps) {
  // Temporarily return null to fix import issues
  return null;

  /* return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(e) => !e.open && onClose()}
      initialFocusEl={() => cancelRef.current}
    >
      <Dialog.Backdrop />
      <Dialog.Positioner>
        <Dialog.Content>
          <Dialog.Header fontSize="lg" fontWeight="bold">
            Delete Transcript
          </Dialog.Header>
          <Dialog.Body>
            Are you sure? You can't undo this action afterwards.
          </Dialog.Body>
          <Dialog.Footer>
            <Button ref={cancelRef} onClick={onClose}>
              Cancel
            </Button>
            <Button colorPalette="red" onClick={onConfirm} ml={3}>
              Delete
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog.Positioner>
    </Dialog.Root>
  ); */
}
