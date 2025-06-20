"use client";

import { useCallback, useEffect, useRef, useState, useContext, RefObject } from "react";
import { Box, Button, Text, VStack, HStack, Spinner, useToast } from "@chakra-ui/react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";
import { useRecordingConsent } from "../recordingConsentContext";
import useApi from "../lib/useApi";
import { Meeting } from '../api';

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

// stages: we focus on the consent, then whereby steals focus, then we focus on the consent again, then return focus to whoever stole it initially
const useConsentWherebyFocusManagement = (acceptButtonRef: RefObject<HTMLButtonElement>, wherebyRef: RefObject<HTMLElement>) => {
  const currentFocusRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (acceptButtonRef.current) {
      acceptButtonRef.current.focus();
    } else {
      console.error("accept button ref not available yet for focus management - seems to be illegal state");
    }

    const handleWherebyReady = () => {
      console.log("whereby ready - refocusing consent button");
      currentFocusRef.current = document.activeElement as HTMLElement;
      if (acceptButtonRef.current) {
        acceptButtonRef.current.focus();
      }
    };

    if (wherebyRef.current) {
      wherebyRef.current.addEventListener("ready", handleWherebyReady);
    } else {
      console.warn("whereby ref not available yet for focus management - seems to be illegal state. not waiting, focus management off.");
    }

    return () => {
      wherebyRef.current?.removeEventListener("ready", handleWherebyReady);
      currentFocusRef.current?.focus();
    };
  }, []);
}

const useConsentDialog = (meetingId: string, wherebyRef: RefObject<HTMLElement>/*accessibility*/) => {
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  const [consentLoading, setConsentLoading] = useState(false);
  // toast would open duplicates, even with using "id=" prop
  const [modalOpen, setModalOpen] = useState(false);
  const api = useApi();
  const toast = useToast();
  
  const handleConsent = useCallback(async (meetingId: string, given: boolean) => {
    if (!api) return;

    setConsentLoading(true);

    try {
      await api.v1MeetingAudioConsent({
        meetingId,
        requestBody: { consent_given: given }
      });

      touch(meetingId);
    } catch (error) {
      console.error('Error submitting consent:', error);
    } finally {
      setConsentLoading(false);
    }
  }, [api, touch]);

  const showConsentModal = useCallback(() => {
    if (modalOpen) return;

    setModalOpen(true);

    const TOAST_NEVER_DISMISS_VALUE = null;
    const toastId = toast({
      position: "top",
      duration: TOAST_NEVER_DISMISS_VALUE,
      render: ({ onClose }) => {
        const AcceptButton = () => {
          const buttonRef = useRef<HTMLButtonElement>(null);
          useConsentWherebyFocusManagement(buttonRef, wherebyRef);
          return (
            <Button
              ref={buttonRef}
              colorScheme="blue"
              size="sm"
              onClick={() => {
                handleConsent(meetingId, true).then(() => {/*signifies it's ok to now wait here.*/})
                onClose()
              }}
            >
              Yes, store the audio
            </Button>
          );
        };

        return (
          <Box p={6} bg="rgba(255, 255, 255, 0.7)" borderRadius="lg" boxShadow="lg" maxW="md" mx="auto">
            <VStack spacing={4} align="center">
              <Text fontSize="md" textAlign="center" fontWeight="medium">
                Can we have your permission to store this meeting's audio recording on our servers?
              </Text>
              <HStack spacing={4} justify="center">
                <AcceptButton />
                <Button
                  colorScheme="gray"
                  size="sm"
                  onClick={() => {
                    handleConsent(meetingId, false).then(() => {/*signifies it's ok to now wait here.*/})
                    onClose()
                  }}
                >
                  No, delete after transcription
                </Button>
              </HStack>
            </VStack>
          </Box>
        );
      },
      onCloseComplete: () => {
        setModalOpen(false);
      }
    });

    // Handle escape key to close the toast
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        toast.close(toastId);
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    const cleanup = () => {
      toast.close(toastId);
      document.removeEventListener('keydown', handleKeyDown);
    };

    return cleanup;
  }, [meetingId, toast, handleConsent, wherebyRef, modalOpen]);

  return { showConsentModal, consentState, hasConsent, consentLoading };
}

function ConsentDialogButton({ meetingId, wherebyRef }: { meetingId: string; wherebyRef: React.RefObject<HTMLElement> }) {
  const { showConsentModal, consentState, hasConsent, consentLoading } = useConsentDialog(meetingId, wherebyRef);

  if (!consentState.ready || hasConsent(meetingId) || consentLoading) {
    return null;
  }

  return (
    <Button
      position="absolute"
      top="56px"
      left="8px"
      zIndex={1000}
      colorScheme="blue"
      size="sm"
      onClick={showConsentModal}
    >
      Meeting is recording
    </Button>
  );
}

const recordingTypeRequiresConsent = (recordingType: NonNullable<Meeting['recording_type']>) => {
  return recordingType === 'cloud';
}

// next throws even with "use client"
const useWhereby = () => {
  const [wherebyLoaded, setWherebyLoaded] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      import("@whereby.com/browser-sdk/embed").then(() => {
        setWherebyLoaded(true);
      }).catch(console.error.bind(console));
    }
  }, []);
  return wherebyLoaded;
}

export default function Room(details: RoomDetails) {
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const roomName = details.params.roomName;
  const meeting = useRoomMeeting(roomName);
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();

  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const meetingId = meeting?.response?.id;

  const recordingType = meeting?.response?.recording_type;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (
      !isLoading &&
      meeting?.error &&
      "status" in meeting.error &&
      meeting.error.status === 404
    ) {
      notFound();
    }
  }, [isLoading, meeting?.error]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !roomUrl || !wherebyLoaded) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isLoading, isAuthenticated, wherebyLoaded]);

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        <Spinner
          thickness="4px"
          speed="0.65s"
          emptyColor="gray.200"
          color="blue.500"
          size="xl"
        />
      </Box>
    );
  }


  return (
    <>
      {roomUrl && meetingId && wherebyLoaded && (
        <>
          <whereby-embed
            ref={wherebyRef}
            room={roomUrl}
            style={{ width: "100vw", height: "100vh" }}
          />
          {recordingType && recordingTypeRequiresConsent(recordingType) && <ConsentDialogButton meetingId={meetingId} wherebyRef={wherebyRef} />}
        </>
      )}
    </>
  );
}
