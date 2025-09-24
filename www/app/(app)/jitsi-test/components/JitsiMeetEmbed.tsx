"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Box, Spinner, Text, VStack } from "@chakra-ui/react";
import {
  JitsiMeetExternalAPI,
  JitsiParticipant,
  JitsiRecordingStatus,
  MeetingState,
  JitsiParticipantEvent,
  JitsiVideoConferenceEvent,
  JitsiErrorEvent,
  JitsiRecordingEvent,
} from "../utils/types";
import {
  loadJitsiScript,
  JITSI_DOMAIN,
  getFullRoomName,
  DEFAULT_CONFIG_OVERWRITE,
  DEFAULT_INTERFACE_CONFIG_OVERWRITE,
} from "../utils/jitsiConfig";
import { toaster } from "../../../components/ui/toaster";

interface JitsiMeetEmbedProps {
  jwt: string;
  roomName: string;
  displayName: string;
  email?: string;
  startWithAudioMuted?: boolean;
  startWithVideoMuted?: boolean;
  onMeetingEnd?: () => void;
  onParticipantJoined?: (participant: JitsiParticipant) => void;
  onParticipantLeft?: (participant: JitsiParticipant) => void;
  onRecordingStatusChanged?: (status: JitsiRecordingStatus) => void;
  onError?: (error: Error) => void;
}

export default function JitsiMeetEmbed({
  jwt,
  roomName,
  displayName,
  email,
  startWithAudioMuted = true,
  startWithVideoMuted = true,
  onMeetingEnd,
  onParticipantJoined,
  onParticipantLeft,
  onRecordingStatusChanged,
  onError,
}: JitsiMeetEmbedProps): JSX.Element {
  const jitsiContainerRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<JitsiMeetExternalAPI | null>(null);
  const [meetingState, setMeetingState] = useState<MeetingState>("loading");
  const [participantCount, setParticipantCount] = useState<number>(0);

  const handleReadyToClose = useCallback(() => {
    console.log("Meeting ended");
    setMeetingState("idle");
    if (onMeetingEnd) {
      onMeetingEnd();
    }
  }, [onMeetingEnd]);

  const handleParticipantJoined = useCallback(
    (event: JitsiParticipantEvent) => {
      const participant: JitsiParticipant = {
        id: event.id,
        displayName: event.displayName || "Guest",
      };
      console.log("Participant joined:", participant);
      setParticipantCount((prev) => prev + 1);
      if (onParticipantJoined) {
        onParticipantJoined(participant);
      }
    },
    [onParticipantJoined],
  );

  const handleParticipantLeft = useCallback(
    (event: JitsiParticipantEvent) => {
      const participant: JitsiParticipant = {
        id: event.id,
        displayName: event.displayName || "Guest",
      };
      console.log("Participant left:", participant);
      setParticipantCount((prev) => Math.max(0, prev - 1));
      if (onParticipantLeft) {
        onParticipantLeft(participant);
      }
    },
    [onParticipantLeft],
  );

  const handleVideoConferenceJoined = useCallback(
    (event: JitsiVideoConferenceEvent) => {
      console.log("Conference joined:", event);
      setMeetingState("joined");
      toaster.create({
        placement: "top",
        duration: 3000,
        render: ({ dismiss }) => (
          <Box
            bg="green.500"
            color="white"
            px={4}
            py={3}
            borderRadius="md"
            display="flex"
            alignItems="center"
            gap={2}
            boxShadow="lg"
          >
            <Text>Successfully joined the meeting</Text>
          </Box>
        ),
      });
    },
    [],
  );

  const handleVideoConferenceLeft = useCallback(
    (event: JitsiVideoConferenceEvent) => {
      console.log("Conference left:", event);
      setMeetingState("idle");
    },
    [],
  );

  const handleRecordingStatusChanged = useCallback(
    (event: JitsiRecordingEvent) => {
      const status: JitsiRecordingStatus = {
        on: event.on,
        mode: event.mode,
      };
      console.log("Recording status changed:", status);
      if (onRecordingStatusChanged) {
        onRecordingStatusChanged(status);
      }

      toaster.create({
        placement: "top",
        duration: 3000,
        render: ({ dismiss }) => (
          <Box
            bg={status.on ? "red.500" : "gray.500"}
            color="white"
            px={4}
            py={3}
            borderRadius="md"
            display="flex"
            alignItems="center"
            gap={2}
            boxShadow="lg"
          >
            <Text>{status.on ? "Recording started" : "Recording stopped"}</Text>
          </Box>
        ),
      });
    },
    [onRecordingStatusChanged],
  );

  const initializeJitsi = useCallback(async () => {
    if (!jitsiContainerRef.current) {
      console.log("Container ref not ready");
      return;
    }

    try {
      console.log("Starting Jitsi initialization...");
      setMeetingState("loading");
      await loadJitsiScript();

      if (!window.JitsiMeetExternalAPI) {
        throw new Error(
          "JitsiMeetExternalAPI not available after loading script",
        );
      }

      console.log("JitsiMeetExternalAPI is available, creating meeting...");
      const fullRoomName = getFullRoomName(roomName);
      console.log("Full room name:", fullRoomName);

      const options = {
        roomName: fullRoomName,
        jwt,
        width: "100%",
        height: "100%",
        parentNode: jitsiContainerRef.current,
        configOverwrite: {
          ...DEFAULT_CONFIG_OVERWRITE,
          startWithAudioMuted,
          startWithVideoMuted,
        },
        interfaceConfigOverwrite: DEFAULT_INTERFACE_CONFIG_OVERWRITE,
        userInfo: {
          displayName,
          email,
        },
        onload: () => {
          console.log("Jitsi iframe loaded");
          setMeetingState("ready");
        },
      };

      console.log("Creating JitsiMeetExternalAPI with options:", options);
      const api = new window.JitsiMeetExternalAPI(JITSI_DOMAIN, options);
      apiRef.current = api;
      console.log("JitsiMeetExternalAPI instance created successfully");

      api.addListener("readyToClose", handleReadyToClose);
      api.addListener("participantJoined", handleParticipantJoined);
      api.addListener("participantLeft", handleParticipantLeft);
      api.addListener("videoConferenceJoined", handleVideoConferenceJoined);
      api.addListener("videoConferenceLeft", handleVideoConferenceLeft);
      api.addListener("recordingStatusChanged", handleRecordingStatusChanged);

      api.addListener("errorOccurred", (error: JitsiErrorEvent) => {
        console.error("Jitsi error:", error);
        if (onError) {
          onError(new Error(error.message || "Unknown Jitsi error"));
        }
      });
    } catch (error) {
      console.error("Failed to initialize Jitsi:", error);
      setMeetingState("error");
      if (onError) {
        onError(error as Error);
      }
      toaster.create({
        placement: "top",
        duration: 5000,
        render: ({ dismiss }) => (
          <Box
            bg="red.500"
            color="white"
            px={4}
            py={3}
            borderRadius="md"
            display="flex"
            alignItems="center"
            gap={2}
            boxShadow="lg"
          >
            <Text>Failed to initialize meeting. Please try again.</Text>
          </Box>
        ),
      });
    }
  }, [
    jwt,
    roomName,
    displayName,
    email,
    startWithAudioMuted,
    startWithVideoMuted,
    handleReadyToClose,
    handleParticipantJoined,
    handleParticipantLeft,
    handleVideoConferenceJoined,
    handleVideoConferenceLeft,
    handleRecordingStatusChanged,
    onError,
  ]);

  useEffect(() => {
    initializeJitsi();

    return () => {
      if (apiRef.current) {
        apiRef.current.dispose();
        apiRef.current = null;
      }
    };
  }, [initializeJitsi]);

  const executeMeetingCommand = useCallback(
    (command: string, ...args: any[]) => {
      if (apiRef.current) {
        apiRef.current.executeCommand(command, ...args);
      }
    },
    [],
  );

  return (
    <Box width="100%" height="100vh" position="relative">
      {meetingState === "error" && (
        <VStack
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          zIndex={10}
          bg="white"
          p={6}
          borderRadius="md"
          boxShadow="lg"
        >
          <Text color="red.500" fontSize="lg">
            Failed to load meeting
          </Text>
          <Text>Please check your connection and try again</Text>
        </VStack>
      )}

      <Box ref={jitsiContainerRef} width="100%" height="100%" bg="gray.900" />
    </Box>
  );
}
