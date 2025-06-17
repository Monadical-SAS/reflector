"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef, useState, useContext } from "react";
import { Box, Button, Text, VStack, HStack, Spinner } from "@chakra-ui/react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";
import AudioConsentDialog from "../(app)/rooms/audioConsentDialog";
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
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [consentLoading, setConsentLoading] = useState(false);
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
  const { api_url } = useContext(DomainContext);
  const { accessToken } = useSessionAccessToken();
  const { id: userId } = useSessionUser();
  const api = useApi();


  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const meetingId = meeting?.response?.id;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  const handleConsent = useCallback(async (meetingId: string, given: boolean) => {
    if (!api) return;

    setShowConsentDialog(false);
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

  // Show consent dialog when meeting is loaded and consent hasn't been answered yet
  useEffect(() => {
    if (
      consentState.ready &&
      meetingId &&
      !hasConsent(meetingId) &&
      !showConsentDialog &&
      !consentLoading
    ) {
      setShowConsentDialog(true);
    }
  }, [consentState.ready, meetingId, hasConsent, showConsentDialog, consentLoading]);

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
      {meetingId && consentState.ready && !hasConsent(meetingId) && !consentLoading && (
        <AudioConsentDialog
          isOpen={showConsentDialog}
          onClose={() => {}} // No-op: ESC should not close without consent
          onConsent={b => handleConsent(meetingId, b)}
        />
      )}
    </>
  );
}
