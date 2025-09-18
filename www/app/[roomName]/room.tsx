"use client";

import { roomMeetingUrl, roomUrl as getRoomUrl } from "../lib/routes";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useContext,
  RefObject,
  use,
} from "react";
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Spinner,
  Icon,
} from "@chakra-ui/react";
import { toaster } from "../components/ui/toaster";
import { useRouter } from "next/navigation";
import { useRecordingConsent } from "../recordingConsentContext";
import {
  useMeetingAudioConsent,
  useRoomGetByName,
  useRoomActiveMeetings,
  useRoomUpcomingMeetings,
  useRoomsCreateMeeting,
  useRoomGetMeeting,
} from "../lib/apiHooks";
import type { components } from "../reflector-api";
import MeetingSelection from "./MeetingSelection";
import useRoomDefaultMeeting from "./useRoomDefaultMeeting";

type Meeting = components["schemas"]["Meeting"];
import { FaBars } from "react-icons/fa6";
import { useAuth } from "../lib/AuthProvider";
import { getWherebyUrl, useWhereby } from "../lib/wherebyClient";
import { useError } from "../(errors)/errorContext";
import {
  assertExistsAndNonEmptyString,
  NonEmptyString,
  parseNonEmptyString,
} from "../lib/utils";
import { printApiError } from "../api/_error";

export type RoomDetails = {
  params: Promise<{
    roomName: string;
    meetingId?: string;
  }>;
};

// stages: we focus on the consent, then whereby steals focus, then we focus on the consent again, then return focus to whoever stole it initially
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
  wherebyRef: RefObject<HTMLElement> /*accessibility*/,
) => {
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  // toast would open duplicates, even with using "id=" prop
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

export default function Room(details: RoomDetails) {
  const params = use(details.params);
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const roomName = parseNonEmptyString(params.roomName);
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";
  const { setError } = useError();

  const roomQuery = useRoomGetByName(roomName);
  const createMeetingMutation = useRoomsCreateMeeting();

  const room = roomQuery.data;

  const pageMeetingId = params.meetingId;

  // this one is called on room page
  const defaultMeeting = useRoomDefaultMeeting(
    room && !room.ics_enabled && !pageMeetingId ? roomName : null,
  );

  const explicitMeeting = useRoomGetMeeting(roomName, pageMeetingId || null);
  const wherebyRoomUrl = explicitMeeting.data
    ? getWherebyUrl(explicitMeeting.data)
    : defaultMeeting.response
      ? getWherebyUrl(defaultMeeting.response)
      : null;
  const recordingType = (explicitMeeting.data || defaultMeeting.response)
    ?.recording_type;
  const meetingId = (explicitMeeting.data || defaultMeeting.response)?.id;

  const isLoading =
    status === "loading" ||
    roomQuery.isLoading ||
    defaultMeeting?.loading ||
    explicitMeeting.isLoading;

  const errors = [
    explicitMeeting.error,
    defaultMeeting.error,
    roomQuery.error,
    createMeetingMutation.error,
  ].filter(Boolean);

  const isOwner =
    isAuthenticated && room ? auth.user?.id === room.user_id : false;

  const handleMeetingSelect = (selectedMeeting: Meeting) => {
    router.push(
      roomMeetingUrl(roomName, parseNonEmptyString(selectedMeeting.id)),
    );
  };

  const handleCreateUnscheduled = async () => {
    try {
      // Create a new unscheduled meeting
      const newMeeting = await createMeetingMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
        body: {
          allow_duplicated: room ? room.ics_enabled : false,
        },
      });
      handleMeetingSelect(newMeeting);
    } catch (err) {
      console.error("Failed to create meeting:", err);
    }
  };

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

  useEffect(() => {
    if (!isLoading && !wherebyRoomUrl) {
      setError(new Error("Whereby room URL not found"));
    }
  }, [isLoading, wherebyRoomUrl]);

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
        <Spinner color="blue.500" size="xl" />
      </Box>
    );
  }

  if (!room) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        <Text fontSize="lg">Room not found</Text>
      </Box>
    );
  }

  if (room.ics_enabled && !params.meetingId) {
    return (
      <MeetingSelection
        roomName={roomName}
        isOwner={isOwner}
        isSharedRoom={room?.is_shared || false}
        authLoading={["loading", "refreshing"].includes(auth.status)}
        onMeetingSelect={handleMeetingSelect}
        onCreateUnscheduled={handleCreateUnscheduled}
        isCreatingMeeting={createMeetingMutation.isPending}
      />
    );
  }

  if (errors.length > 0) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        {errors.map((error, i) => (
          <Text key={i} fontSize="lg">
            {printApiError(error)}
          </Text>
        ))}
      </Box>
    );
  }

  return (
    <>
      {wherebyRoomUrl && wherebyLoaded && (
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
                meetingId={assertExistsAndNonEmptyString(
                  meetingId,
                  "panic! no meetingId",
                )}
                wherebyRef={wherebyRef}
              />
            )}
        </>
      )}
    </>
  );
}
