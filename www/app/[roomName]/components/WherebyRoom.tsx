"use client";

import { useCallback, useEffect, useRef, useState, RefObject } from "react";
import { Box, Button, Text, VStack, HStack, Icon } from "@chakra-ui/react";
import { toaster } from "../../components/ui/toaster";
import { useRouter } from "next/navigation";
import { useRecordingConsent } from "../../recordingConsentContext";
import { useMeetingAudioConsent } from "../../lib/apiHooks";
import type { components } from "../../reflector-api";
import { FaBars } from "react-icons/fa6";
import { useAuth } from "../../lib/AuthProvider";
import { getWherebyUrl, useWhereby } from "../../lib/wherebyClient";
import { assertExistsAndNonEmptyString, NonEmptyString } from "../../lib/utils";

type Meeting = components["schemas"]["Meeting"];

interface WherebyRoomProps {
  meeting: Meeting;
}

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
  const [modalOpen, setModalOpen] = useState(false);
  const audioConsentMutation = useMeetingAudioConsent();

  const handleConsent = useCallback(
    async (meetingId: string, given: boolean) => {
      try {
        await audioConsentMutation.mutateAsync({
          params: {
            path: {
              meeting_id: meetingId,
            },
          },
          body: {
            consent_given: given,
          },
        });

        touch(meetingId);
      } catch (error) {
        console.error("Error submitting consent:", error);
      }
    },
    [audioConsentMutation, touch],
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

    toastId.then((id) => {
      const checkToastStatus = setInterval(() => {
        if (!toaster.isActive(id)) {
          setModalOpen(false);
          clearInterval(checkToastStatus);
        }
      }, 100);
    });

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

  return {
    showConsentModal,
    consentState,
    hasConsent,
    consentLoading: audioConsentMutation.isPending,
  };
};

function ConsentDialogButton({
  meetingId,
  wherebyRef,
}: {
  meetingId: NonEmptyString;
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

const recordingTypeRequiresConsent = (
  recordingType: NonNullable<Meeting["recording_type"]>,
) => {
  return recordingType === "cloud";
};

export default function WherebyRoom({ meeting }: WherebyRoomProps) {
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";

  const wherebyRoomUrl = getWherebyUrl(meeting);
  const recordingType = meeting.recording_type;
  const meetingId = meeting.id;

  const isLoading = status === "loading";

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !wherebyRoomUrl || !wherebyLoaded)
      return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, wherebyRoomUrl, isLoading, isAuthenticated, wherebyLoaded]);

  if (!wherebyRoomUrl || !wherebyLoaded) {
    return null;
  }

  return (
    <>
      <whereby-embed
        ref={wherebyRef}
        room={wherebyRoomUrl}
        style={{ width: "100vw", height: "100vh" }}
      />
      {recordingType &&
        recordingTypeRequiresConsent(recordingType) &&
        meetingId && (
          <ConsentDialogButton
            meetingId={assertExistsAndNonEmptyString(meetingId)}
            wherebyRef={wherebyRef}
          />
        )}
    </>
  );
}
