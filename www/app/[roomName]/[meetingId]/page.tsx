"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  HStack,
  Icon,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import {
  useRoomGetByName,
  useRoomJoinMeeting,
  useMeetingAudioConsent,
} from "../../lib/apiHooks";
import { useRecordingConsent } from "../../recordingConsentContext";
import { toaster } from "../../components/ui/toaster";
import { FaBars } from "react-icons/fa6";
import MeetingMinimalHeader from "../../components/MeetingMinimalHeader";
import type { components } from "../../reflector-api";

type Meeting = components["schemas"]["Meeting"];

// next throws even with "use client"
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

// Consent functionality from main branch
const useConsentWherebyFocusManagement = (
  acceptButtonRef: React.RefObject<HTMLButtonElement>,
  wherebyRef: React.RefObject<HTMLElement>,
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
  wherebyRef: React.RefObject<HTMLElement>,
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

const recordingTypeRequiresConsent = (
  recordingType: NonNullable<Meeting["recording_type"]>,
) => {
  return recordingType === "cloud";
};
interface MeetingPageProps {
  params: {
    roomName: string;
    meetingId: string;
  };
}

export default function MeetingPage({ params }: MeetingPageProps) {
  const { roomName, meetingId } = params;
  const router = useRouter();
  const [attemptedJoin, setAttemptedJoin] = useState(false);
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);

  // Fetch room data
  const roomQuery = useRoomGetByName(roomName);
  const joinMeetingMutation = useRoomJoinMeeting();

  const room = roomQuery.data;
  const isLoading =
    roomQuery.isLoading ||
    (!attemptedJoin && room && !joinMeetingMutation.data);

  // Try to join the meeting when room is loaded
  useEffect(() => {
    if (room && !attemptedJoin && !joinMeetingMutation.isPending) {
      setAttemptedJoin(true);
      joinMeetingMutation.mutate({
        params: {
          path: {
            room_name: roomName,
            meeting_id: meetingId,
          },
        },
      });
    }
  }, [room, attemptedJoin, joinMeetingMutation, roomName, meetingId]);

  // Redirect to room lobby if meeting join fails (meeting finished/not found)
  useEffect(() => {
    if (joinMeetingMutation.isError || roomQuery.isError) {
      router.push(`/${roomName}`);
    }
  }, [joinMeetingMutation.isError, roomQuery.isError, router, roomName]);

  // Get meeting data from join response
  const meeting = joinMeetingMutation.data;
  const roomUrl = meeting?.host_room_url || meeting?.room_url;
  const recordingType = meeting?.recording_type;

  const handleLeave = useCallback(() => {
    router.push(`/${roomName}`);
  }, [router, roomName]);

  useEffect(() => {
    if (!isLoading && !roomUrl && !wherebyLoaded) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isLoading, wherebyLoaded]);

  if (isLoading) {
    return (
      <Box display="flex" flexDirection="column" minH="100vh">
        <MeetingMinimalHeader
          roomName={roomName}
          displayName={room?.name}
          showLeaveButton={false}
        />
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          flex="1"
          bg="gray.50"
          p={4}
        >
          <VStack gap={4}>
            <Spinner color="blue.500" size="xl" />
            <Text fontSize="lg">Loading meeting...</Text>
          </VStack>
        </Box>
      </Box>
    );
  }

  // If we have a successful meeting join with room URL, show Whereby embed
  if (meeting && roomUrl && wherebyLoaded) {
    return (
      <>
        <whereby-embed
          ref={wherebyRef}
          room={roomUrl}
          style={{ width: "100vw", height: "100vh" }}
        />
        {recordingType && recordingTypeRequiresConsent(recordingType) && (
          <ConsentDialogButton meetingId={meetingId} wherebyRef={wherebyRef} />
        )}
      </>
    );
  }

  // This return should not be reached normally since we redirect on errors
  // But keeping it as a fallback
  return (
    <Box display="flex" flexDirection="column" minH="100vh">
      <MeetingMinimalHeader roomName={roomName} displayName={room?.name} />
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        flex="1"
        bg="gray.50"
        p={4}
      >
        <Text fontSize="lg">Meeting not available</Text>
      </Box>
    </Box>
  );
}
