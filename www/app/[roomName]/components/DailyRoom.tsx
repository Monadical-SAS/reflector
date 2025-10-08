"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Button, Text, VStack, HStack, Icon } from "@chakra-ui/react";
import { toaster } from "../../components/ui/toaster";
import { useRouter } from "next/navigation";
import { useRecordingConsent } from "../../recordingConsentContext";
import { useMeetingAudioConsent } from "../../lib/apiHooks";
import { FaBars } from "react-icons/fa6";
import DailyIframe, { DailyCall } from "@daily-co/daily-js";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";

type Meeting = components["schemas"]["Meeting"];

const CONSENT_BUTTON_TOP_OFFSET = "56px";
const TOAST_CHECK_INTERVAL_MS = 100;

interface DailyRoomProps {
  meeting: Meeting;
}

function ConsentDialogButton({ meetingId }: { meetingId: string }) {
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
      render: ({ dismiss }) => (
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
              <Button
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
            </HStack>
          </VStack>
        </Box>
      ),
    });

    toastId.then((id) => {
      const checkToastStatus = setInterval(() => {
        if (!toaster.isActive(id)) {
          setModalOpen(false);
          clearInterval(checkToastStatus);
        }
      }, TOAST_CHECK_INTERVAL_MS);
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
  }, [meetingId, handleConsent, modalOpen]);

  if (
    !consentState.ready ||
    hasConsent(meetingId) ||
    audioConsentMutation.isPending
  ) {
    return null;
  }

  return (
    <Button
      position="absolute"
      top={CONSENT_BUTTON_TOP_OFFSET}
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
  recordingType: Meeting["recording_type"],
) => {
  return recordingType === "cloud";
};

export default function DailyRoom({ meeting }: DailyRoomProps) {
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";
  const [callFrame, setCallFrame] = useState<DailyCall | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const roomUrl = meeting?.host_room_url || meeting?.room_url;

  const isLoading = status === "loading";

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (isLoading || !roomUrl || !containerRef.current) return;

    let frame: DailyCall | null = null;
    let destroyed = false;

    const createAndJoin = async () => {
      try {
        const existingFrame = DailyIframe.getCallInstance();
        if (existingFrame) {
          await existingFrame.destroy();
        }

        frame = DailyIframe.createFrame(containerRef.current!, {
          iframeStyle: {
            width: "100vw",
            height: "100vh",
            border: "none",
          },
          showLeaveButton: true,
          showFullscreenButton: true,
        });

        if (destroyed) {
          await frame.destroy();
          return;
        }

        frame.on("left-meeting", handleLeave);
        await frame.join({ url: roomUrl });

        if (!destroyed) {
          setCallFrame(frame);
        }
      } catch (error) {
        console.error("Error creating Daily frame:", error);
      }
    };

    createAndJoin();

    return () => {
      destroyed = true;
      if (frame) {
        frame.destroy().catch((e) => {
          console.error("Error destroying frame:", e);
        });
      }
    };
  }, [roomUrl, isLoading, handleLeave]);

  if (!roomUrl) {
    return null;
  }

  return (
    <Box position="relative" width="100vw" height="100vh">
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {recordingTypeRequiresConsent(meeting.recording_type) && (
        <ConsentDialogButton meetingId={meeting.id} />
      )}
    </Box>
  );
}
