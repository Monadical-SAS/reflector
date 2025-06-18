"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef, useState, useContext } from "react";
import { Box, Button, Text, VStack, HStack, Spinner, useToast } from "@chakra-ui/react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";
import { DomainContext } from "../domainContext";
import { useRecordingConsent } from "../recordingConsentContext";
import useSessionAccessToken from "../lib/useSessionAccessToken";
import useSessionUser from "../lib/useSessionUser";
import useApi from "../lib/useApi";

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

export default function Room(details: RoomDetails) {
  const wherebyRef = useRef<HTMLElement>(null);
  const roomName = details.params.roomName;
  const meeting = useRoomMeeting(roomName);
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();
  const [consentLoading, setConsentLoading] = useState(false);
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  const { api_url } = useContext(DomainContext);
  const { accessToken } = useSessionAccessToken();
  const { id: userId } = useSessionUser();
  const api = useApi();
  const toast = useToast();


  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const meetingId = meeting?.response?.id;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  const handleConsent = useCallback(async (meetingId: string, given: boolean, onClose?: () => void) => {
    if (!api) return;

    if (onClose) onClose();
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
                  onClick={() => handleConsent(meetingId, true, onClose)}
                >
                  Yes, store the audio
                </Button>
                <Button 
                  colorScheme="red" 
                  size="sm"
                  onClick={() => handleConsent(meetingId, false, onClose)}
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
      {roomUrl && (
        <whereby-embed
          ref={wherebyRef}
          room={roomUrl}
          style={{ width: "100vw", height: "100vh" }}
        />
      )}
    </>
  );
}
