"use client";

import { useCallback, useEffect, useRef, useState, RefObject } from "react";
import { Box, Button, Text, VStack, HStack, Icon } from "@chakra-ui/react";
import { toaster } from "../../components/ui/toaster";
import { useRouter } from "next/navigation";
import useSessionStatus from "../../lib/useSessionStatus";
import { useRecordingConsent } from "../../recordingConsentContext";
import useApi from "../../lib/useApi";
import { FaBars } from "react-icons/fa6";
import type { Meeting, recording_type } from "../../api/types.gen";

interface WherebyRoomProps {
  meeting: Meeting;
}

// Focus management for Whereby embed and consent dialog
const useConsentWherebyFocusManagement = (
  acceptButtonRef: RefObject<HTMLButtonElement>,
  wherebyRef: RefObject<HTMLElement>,
) => {
  const currentFocusRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (acceptButtonRef.current) {
      acceptButtonRef.current.focus();
    } else {
      console.error(
        "accept button ref not available yet for focus management - seems to be illegal state",
      );
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
      console.warn(
        "whereby ref not available yet for focus management - seems to be illegal state. not waiting, focus management off.",
      );
    }

    return () => {
      wherebyRef.current?.removeEventListener("ready", handleWherebyReady);
      currentFocusRef.current?.focus();
    };
  }, []);
};

const useConsentDialog = (
  meetingId: string,
  wherebyRef: RefObject<HTMLElement>,
) => {
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  const [consentLoading, setConsentLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const api = useApi();

  const handleConsent = useCallback(
    async (meetingId: string, given: boolean) => {
      if (!api) return;

      setConsentLoading(true);

      try {
        await api.v1MeetingAudioConsent({
          meetingId,
          requestBody: { consent_given: given },
        });

        touch(meetingId);
      } catch (error) {
        console.error("Error submitting consent:", error);
      } finally {
        setConsentLoading(false);
      }
    },
    [api, touch],
  );

  const showConsentModal = useCallback(() => {
    if (modalOpen) return;

    setModalOpen(true);

    const toastId = toaster.create({
      placement: "top",
      duration: null,
      render: ({ dismiss }) => {
        const AcceptButton = () => {
          const buttonRef = useRef<HTMLButtonElement>(null);
          useConsentWherebyFocusManagement(buttonRef, wherebyRef);
          return (
            <Button
              ref={buttonRef}
              colorPalette="primary"
              size="sm"
              onClick={() => {
                handleConsent(meetingId, true).then(() => {
                  /*signifies it's ok to now wait here.*/
                });
                dismiss();
              }}
            >
              Yes, store the audio
            </Button>
          );
        };

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
                Can we have your permission to store this meeting's audio
                recording on our servers?
              </Text>
              <HStack gap={4} justifyContent="center">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    handleConsent(meetingId, false).then(() => {
                      /*signifies it's ok to now wait here.*/
                    });
                    dismiss();
                  }}
                >
                  No, delete after transcription
                </Button>
                <AcceptButton />
              </HStack>
            </VStack>
          </Box>
        );
      },
    });

    // Set modal state when toast is dismissed
    toastId.then((id) => {
      const checkToastStatus = setInterval(() => {
        if (!toaster.isActive(id)) {
          setModalOpen(false);
          clearInterval(checkToastStatus);
        }
      }, 100);
    });

    // Handle escape key to close the toast
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        toastId.then((id) => toaster.dismiss(id));
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    const cleanup = () => {
      toastId.then((id) => toaster.dismiss(id));
      document.removeEventListener("keydown", handleKeyDown);
    };

    return cleanup;
  }, [meetingId, handleConsent, wherebyRef, modalOpen]);

  return { showConsentModal, consentState, hasConsent, consentLoading };
};

function ConsentDialogButton({
  meetingId,
  wherebyRef,
}: {
  meetingId: string;
  wherebyRef: React.RefObject<HTMLElement>;
}) {
  const { showConsentModal, consentState, hasConsent, consentLoading } =
    useConsentDialog(meetingId, wherebyRef);

  if (!consentState.ready || hasConsent(meetingId) || consentLoading) {
    return null;
  }

  return (
    <Button
      position="absolute"
      top="56px"
      left="8px"
      zIndex={1000}
      colorPalette="blue"
      size="sm"
      onClick={showConsentModal}
    >
      Meeting is being recorded
      <Icon as={FaBars} ml={2} />
    </Button>
  );
}

const recordingTypeRequiresConsent = (recordingType: recording_type | undefined) => {
  return recordingType === "cloud";
};

// Whereby SDK loading hook
const useWhereby = () => {
  const [wherebyLoaded, setWherebyLoaded] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined") {
      import("@whereby.com/browser-sdk/embed")
        .then(() => {
          setWherebyLoaded(true);
        })
        .catch(console.error.bind(console));
    }
  }, []);
  return wherebyLoaded;
};

export default function WherebyRoom({ meeting }: WherebyRoomProps) {
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();

  const roomUrl = meeting?.host_room_url
    ? meeting?.host_room_url
    : meeting?.room_url;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !roomUrl || !wherebyLoaded) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isLoading, isAuthenticated, wherebyLoaded]);

  if (!roomUrl || !wherebyLoaded) {
    return null;
  }

  return (
    <>
      <whereby-embed
        ref={wherebyRef}
        room={roomUrl}
        style={{ width: "100vw", height: "100vh" }}
      />
      {recordingTypeRequiresConsent(meeting.recording_type) && (
        <ConsentDialogButton meetingId={meeting.id} wherebyRef={wherebyRef} />
      )}
    </>
  );
}
