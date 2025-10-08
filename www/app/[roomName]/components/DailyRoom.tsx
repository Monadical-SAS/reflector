"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Button, Text, VStack, HStack, Icon } from "@chakra-ui/react";
import { toaster } from "../../components/ui/toaster";
import { useRouter } from "next/navigation";
import useSessionStatus from "../../lib/useSessionStatus";
import { useRecordingConsent } from "../../recordingConsentContext";
import useApi from "../../lib/useApi";
import { FaBars } from "react-icons/fa6";
import DailyIframe, { DailyCall } from "@daily-co/daily-js";
import type { Meeting, recording_type } from "../../api/types.gen";

const CONSENT_BUTTON_TOP_OFFSET = "56px";
const TOAST_CHECK_INTERVAL_MS = 100;

interface DailyRoomProps {
  meeting: Meeting;
}

function ConsentDialogButton({ meetingId }: { meetingId: string }) {
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

    // Set modal state when toast is dismissed
    toastId.then((id) => {
      const checkToastStatus = setInterval(() => {
        if (!toaster.isActive(id)) {
          setModalOpen(false);
          clearInterval(checkToastStatus);
        }
      }, TOAST_CHECK_INTERVAL_MS);
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
  }, [meetingId, handleConsent, modalOpen]);

  if (!consentState.ready || hasConsent(meetingId) || consentLoading) {
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

const recordingTypeRequiresConsent = (recordingType: recording_type | undefined) => {
  return recordingType === "cloud";
};

export default function DailyRoom({ meeting }: DailyRoomProps) {
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();
  const [callFrame, setCallFrame] = useState<DailyCall | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const roomUrl = meeting?.host_room_url
    ? meeting?.host_room_url
    : meeting?.room_url;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  // Initialize Daily.co call frame
  useEffect(() => {
    if (isLoading || !isAuthenticated || !roomUrl) return;

    const frame = DailyIframe.createFrame(containerRef.current!, {
      iframeStyle: {
        width: "100vw",
        height: "100vh",
        border: "none",
      },
      showLeaveButton: true,
      showFullscreenButton: true,
    });

    frame.on("left-meeting", handleLeave);

    frame.join({ url: roomUrl });

    setCallFrame(frame);

    return () => {
      frame.destroy();
    };
  }, [roomUrl, isLoading, isAuthenticated, handleLeave]);

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
