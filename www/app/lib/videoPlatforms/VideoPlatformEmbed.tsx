"use client";

import { useCallback, useEffect, useRef, useState, RefObject } from "react";
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Spinner,
  Icon,
} from "@chakra-ui/react";
import { FaBars } from "react-icons/fa6";
import { Meeting, VideoPlatform } from "../../api";
import { getVideoPlatformAdapter, getCurrentVideoPlatform } from "./factory";
import { useRecordingConsent } from "../../recordingConsentContext";
import { toaster } from "../../components/ui/toaster";
import useApi from "../useApi";

interface VideoPlatformEmbedProps {
  meeting: Meeting;
  platform?: VideoPlatform;
  onLeave?: () => void;
  onReady?: () => void;
}

// Focus management hook for platforms that support it
const usePlatformFocusManagement = (
  acceptButtonRef: RefObject<HTMLButtonElement>,
  platformRef: RefObject<HTMLElement>,
  supportsFocusManagement: boolean,
) => {
  const currentFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!supportsFocusManagement) return;

    if (acceptButtonRef.current) {
      acceptButtonRef.current.focus();
    } else {
      console.error(
        "accept button ref not available yet for focus management - seems to be illegal state",
      );
    }

    const handlePlatformReady = () => {
      console.log("platform ready - refocusing consent button");
      currentFocusRef.current = document.activeElement as HTMLElement;
      if (acceptButtonRef.current) {
        acceptButtonRef.current.focus();
      }
    };

    if (platformRef.current) {
      platformRef.current.addEventListener("ready", handlePlatformReady);
    } else {
      console.warn(
        "platform ref not available yet for focus management - seems to be illegal state. not waiting, focus management off.",
      );
    }

    return () => {
      platformRef.current?.removeEventListener("ready", handlePlatformReady);
      currentFocusRef.current?.focus();
    };
  }, [acceptButtonRef, platformRef, supportsFocusManagement]);
};

const useConsentDialog = (
  meetingId: string,
  platformRef: RefObject<HTMLElement>,
  supportsFocusManagement: boolean,
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
          usePlatformFocusManagement(
            buttonRef,
            platformRef,
            supportsFocusManagement,
          );
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
  }, [
    meetingId,
    handleConsent,
    platformRef,
    modalOpen,
    supportsFocusManagement,
  ]);

  return { showConsentModal, consentState, hasConsent, consentLoading };
};

function ConsentDialogButton({
  meetingId,
  platformRef,
  supportsFocusManagement,
}: {
  meetingId: string;
  platformRef: React.RefObject<HTMLElement>;
  supportsFocusManagement: boolean;
}) {
  const { showConsentModal, consentState, hasConsent, consentLoading } =
    useConsentDialog(meetingId, platformRef, supportsFocusManagement);

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

const recordingTypeRequiresConsent = (
  recordingType: NonNullable<Meeting["recording_type"]>,
) => {
  return recordingType === "cloud";
};

export default function VideoPlatformEmbed({
  meeting,
  platform,
  onLeave,
  onReady,
}: VideoPlatformEmbedProps) {
  const platformRef = useRef<HTMLElement>(null);
  const selectedPlatform = platform || getCurrentVideoPlatform();
  const adapter = getVideoPlatformAdapter(selectedPlatform);
  const PlatformComponent = adapter.component;

  const meetingId = meeting.id;
  const recordingType = meeting.recording_type;

  // Handle leave event
  const handleLeave = useCallback(() => {
    if (onLeave) {
      onLeave();
    }
  }, [onLeave]);

  // Handle ready event
  const handleReady = useCallback(() => {
    if (onReady) {
      onReady();
    }
  }, [onReady]);

  // Set up leave event listener for platforms that support it
  useEffect(() => {
    if (!platformRef.current) return;

    const element = platformRef.current;
    element.addEventListener("leave", handleLeave);

    return () => {
      element.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave]);

  return (
    <>
      <PlatformComponent
        ref={platformRef}
        meeting={meeting}
        roomRef={platformRef}
        onReady={handleReady}
      />
      {recordingType &&
        recordingTypeRequiresConsent(recordingType) &&
        adapter.requiresConsent && (
          <ConsentDialogButton
            meetingId={meetingId}
            platformRef={platformRef}
            supportsFocusManagement={adapter.supportsFocusManagement}
          />
        )}
    </>
  );
}
