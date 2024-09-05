"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Button, Text, VStack, HStack } from "@chakra-ui/react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";

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
  const { isReady, isAuthenticated } = useSessionStatus();

  const [consentGiven, setConsentGiven] = useState<boolean | null>(null);

  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  const handleConsent = (consent: boolean) => {
    setConsentGiven(consent);
  };

  useEffect(() => {
    if (!isReady || !isAuthenticated || !roomUrl) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isReady, isAuthenticated]);

  if (!isReady && !isAuthenticated && !consentGiven) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
        bg="gray.50"
        p={4}
      >
        <VStack
          spacing={6}
          p={10}
          width="400px"
          bg="white"
          borderRadius="md"
          shadow="md"
          textAlign="center"
        >
          {consentGiven === null ? (
            <>
              <Text fontSize="lg" fontWeight="bold">
                This meeting may be recorded. Do you consent to being recorded?
              </Text>
              <HStack spacing={4}>
                <Button variant="outline" onClick={() => handleConsent(false)}>
                  No, I do not consent
                </Button>
                <Button colorScheme="blue" onClick={() => handleConsent(true)}>
                  Yes, I consent
                </Button>
              </HStack>
            </>
          ) : (
            <>
              <Text fontSize="lg" fontWeight="bold">
                You cannot join the meeting without consenting to being
                recorded.
              </Text>
            </>
          )}
        </VStack>
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
