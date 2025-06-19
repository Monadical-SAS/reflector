"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef, useState, useContext } from "react";
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

const useConsentDialog = (meetingId: string) => {
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  const [consentLoading, setConsentLoading] = useState(false);
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

  // Show consent toast when meeting is loaded and consent hasn't been answered yet
  useEffect(() => {
    if (
      consentState.ready &&
      meetingId &&
      !hasConsent(meetingId) &&
      !consentLoading
    ) {
      const toastId = toast({
        position: "top",
        duration: null,
        render: ({ onClose }) => (
          <Box p={4} bg="white" borderRadius="md" boxShadow="md">
            <VStack spacing={3} align="stretch">
              <Text>
                Can we have your permission to store this meeting's audio recording on our servers?
              </Text>
              <HStack spacing={4} justify="center">
                <Button
                  colorScheme="green"
                  size="sm"
                  onClick={() => {
                    handleConsent(meetingId, true).then(() => {/*signifies it's ok to now wait here.*/})
                    onClose()
                  }}
                >
                  Yes, store the audio
                </Button>
                <Button
                  colorScheme="red"
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
        ),
      });

      return () => {
        toast.close(toastId);
      };
    }
  }, [consentState.ready, meetingId, hasConsent, consentLoading, toast, handleConsent]);
}

function ConsentDialog({ meetingId }: { meetingId: string }) {
  useConsentDialog(meetingId);
  return <></>
}

const recordingTypeRequiresConsent = (recordingType: NonNullable<Meeting['recording_type']>) => {
  return recordingType === 'cloud';
}

export default function Room(details: RoomDetails) {
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
    if (isLoading || !isAuthenticated || !roomUrl) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isLoading, isAuthenticated]);

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
      {roomUrl && meetingId && (
        <>
          <whereby-embed
            ref={wherebyRef}
            room={roomUrl}
            style={{ width: "100vw", height: "100vh" }}
          />
          {recordingType && recordingTypeRequiresConsent(recordingType) && <ConsentDialog meetingId={meetingId} />}
        </>
      )}
    </>
  );
}
