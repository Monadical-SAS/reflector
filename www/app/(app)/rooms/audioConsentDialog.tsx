import React from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  Text,
  HStack,
} from "@chakra-ui/react";

interface AudioConsentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConsent: (given: boolean) => void;
}

const AudioConsentDialog = ({ isOpen, onClose, onConsent }: AudioConsentDialogProps) => {
  const handleConsent = (given: boolean) => {
    onConsent(given);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={false} closeOnEsc={false}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Audio Storage Consent</ModalHeader>
        <ModalBody pb={6}>
          <Text mb={4}>
            Can we have your permission to store this meeting's audio recording on our servers?
          </Text>
          <HStack spacing={4}>
            <Button colorScheme="green" onClick={() => handleConsent(true)}>
              Yes, store the audio
            </Button>
            <Button colorScheme="red" onClick={() => handleConsent(false)}>
              No, delete after transcription
            </Button>
          </HStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default AudioConsentDialog;