"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Button, Text, VStack, HStack, Spinner } from "@chakra-ui/react";
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
  const { isLoading, isAuthenticated } = useSessionStatus();

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
    if (isLoading || !isAuthenticated || !roomUrl) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl, isLoading, isAuthenticated]);

  // useEffect(() => {
  //   if (!wherebyRef.current || !roomUrl) return;

  //   const handleEvent = (event: any) => {
  //     console.log(`WEV ${event.type}`, event.detail || event);
  //   };

  //   const events = [
  //     "ready",
  //     "precall_check_skipped",
  //     "precall_check_completed",
  //     "knock",
  //     "participantupdate",
  //     "join",
  //     "leave",
  //     "participant_join",
  //     "participant_leave",
  //     "microphone_toggle",
  //     "camera_toggle",
  //     "chat_toggle",
  //     "people_toggle",
  //     "pip_toggle",
  //     "deny_device_permission",
  //     "screenshare_toggle",
  //     "streaming_status_change",
  //     "connection_status_change",
  //     "meeting_end",
  //   ];

  //   const element = wherebyRef.current;

  //   events.forEach((eventName) => {
  //     element.addEventListener(eventName, handleEvent);
  //   });

  //   return () => {
  //     events.forEach((eventName) => {
  //       element.removeEventListener(eventName, handleEvent);
  //     });
  //   };
  // }, [roomUrl, router]);

  useEffect(() => {
    if (!roomUrl) return;

    const handleJoin = () => {
      meeting.startKeepalive();
    };

    const handleLeave = () => {
      meeting.stopKeepalive();
    };

    wherebyRef.current?.addEventListener("join", handleJoin);
    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("join", handleJoin);
      wherebyRef.current?.removeEventListener("leave", handleLeave);
      meeting.stopKeepalive();
    };
  }, [roomUrl, meeting.startKeepalive, meeting.stopKeepalive]);

  useEffect(() => {
    if (!roomUrl) return;

    const handleEndMeeting = () => {
      meeting.endMeeting();
    };

    wherebyRef.current?.addEventListener("meeting_end", handleEndMeeting);

    return () => {
      wherebyRef.current?.removeEventListener("meeting_end", handleEndMeeting);
    };
  }, [roomUrl, meeting.endMeeting]);

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

  if (!isAuthenticated && !consentGiven) {
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
