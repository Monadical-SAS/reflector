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
import useSessionAccessToken from "../lib/useSessionAccessToken";
import useSessionUser from "../lib/useSessionUser";

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
  const [consentGiven, setConsentGiven] = useState<boolean | null>(null);
  const { api_url } = useContext(DomainContext);
  const { accessToken } = useSessionAccessToken();
  const { id: userId } = useSessionUser();


  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  const getUserIdentifier = useCallback(() => {
    if (isAuthenticated && userId) {
      return userId; // Send actual user ID for authenticated users
    }
    
    // For anonymous users, send no identifier
    return null;
  }, [isAuthenticated, userId]);

  const handleConsent = useCallback(async (given: boolean) => {
    setConsentGiven(given);
    setShowConsentDialog(false); // Close dialog after consent is given
    
    if (meeting?.response?.id && api_url) {
      try {
        const userIdentifier = getUserIdentifier();
        const requestBody: any = {
          consent_given: given
        };
        
        // Only include user_identifier if we have one (authenticated users)
        if (userIdentifier) {
          requestBody.user_identifier = userIdentifier;
        }
        
        const response = await fetch(`${api_url}/v1/meetings/${meeting.response.id}/consent`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken && { 'Authorization': `Bearer ${accessToken}` })
          },
          body: JSON.stringify(requestBody),
        });
        
        if (!response.ok) {
          console.error('Failed to submit consent');
        }
      } catch (error) {
        console.error('Error submitting consent:', error);
      }
    }
  }, [meeting?.response?.id, api_url, accessToken]);


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

  // Show consent dialog when meeting is loaded and consent hasn't been given yet
  useEffect(() => {
    if (meeting?.response?.id && consentGiven === null && !showConsentDialog) {
      setShowConsentDialog(true);
    }
  }, [meeting?.response?.id, consentGiven, showConsentDialog]);

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
      <AudioConsentDialog
        isOpen={showConsentDialog}
        onClose={() => {}} // No-op: ESC should not close without consent
        onConsent={handleConsent}
      />
    </>
  );
}
