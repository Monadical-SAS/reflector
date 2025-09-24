"use client";

import { useState, useCallback } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Badge,
  Heading,
  Code,
} from "@chakra-ui/react";
import JitsiControls from "./components/JitsiControls";
import JitsiMeetSDK from "./components/JitsiMeetSDK";
import {
  MeetingConfig,
  MeetingState,
  JitsiParticipant,
  JitsiRecordingStatus,
} from "./utils/types";
import { generateJitsiJWT, decodeJWT } from "./utils/jwtGenerator";
import { toaster } from "../../components/ui/toaster";
import { FaArrowLeft, FaInfo } from "react-icons/fa";

export default function JitsiTestPage(): JSX.Element {
  const [meetingState, setMeetingState] = useState<MeetingState>({
    type: "idle",
  });
  const [isGeneratingToken, setIsGeneratingToken] = useState<boolean>(false);
  const [participants, setParticipants] = useState<JitsiParticipant[]>([]);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [debugInfo, setDebugInfo] = useState<string>("");

  const handleJoinMeeting = useCallback(async (config: MeetingConfig) => {
    setIsGeneratingToken(true);
    setMeetingState({ type: "generating" });

    try {
      const jwt = await generateJitsiJWT({
        roomName: config.roomName,
        user: {
          id: `user-${crypto.randomUUID()}`,
          name: config.displayName,
          email: config.email,
          moderator: config.isModerator ? "true" : "false",
        },
        features: {
          recording: config.enableRecording,
          transcription: config.enableTranscription,
          livestreaming: config.enableLivestreaming,
        },
      });

      // Only show debug info in development environment
      if (process.env.NODE_ENV === "development") {
        const decoded = decodeJWT(jwt);
        setDebugInfo(JSON.stringify(decoded, null, 2));
      }
      setMeetingState({
        type: "ready",
        config,
        token: jwt,
      });

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
            <Text>JWT token generated successfully</Text>
          </Box>
        ),
      });
    } catch (error) {
      console.error("Failed to generate JWT:", error);
      setMeetingState({
        type: "error",
        error:
          error instanceof Error ? error : new Error("Failed to generate JWT"),
      });
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
            <Text>
              Failed to generate JWT token. Please check the configuration.
            </Text>
          </Box>
        ),
      });
    } finally {
      setIsGeneratingToken(false);
    }
  }, []);

  const handleMeetingEnd = useCallback(() => {
    setMeetingState({ type: "idle" });
    setParticipants([]);
    setIsRecording(false);
    setDebugInfo("");
  }, []);

  const handleParticipantJoined = useCallback(
    (participant: JitsiParticipant) => {
      setParticipants((prev) => [...prev, participant]);
    },
    [],
  );

  const handleParticipantLeft = useCallback((participant: JitsiParticipant) => {
    setParticipants((prev) => prev.filter((p) => p.id !== participant.id));
  }, []);

  const handleRecordingStatusChanged = useCallback(
    (status: JitsiRecordingStatus) => {
      setIsRecording(status.on);
    },
    [],
  );

  if (meetingState.type === "ready") {
    return (
      <Box width="100vw" height="100vh" position="relative">
        <Box
          position="absolute"
          top={4}
          left={4}
          zIndex={10}
          bg="white"
          p={3}
          borderRadius="md"
          boxShadow="md"
        >
          <VStack align="start" spacing={2}>
            <HStack>
              <Button
                size="sm"
                leftIcon={<FaArrowLeft />}
                onClick={handleMeetingEnd}
                colorScheme="red"
              >
                Leave Meeting
              </Button>
              {isRecording && (
                <Badge colorScheme="red" variant="solid">
                  Recording
                </Badge>
              )}
            </HStack>
            <HStack>
              <Text fontSize="sm">
                Room: <strong>{meetingState.config.roomName}</strong>
              </Text>
              <Badge>{participants.length} participants</Badge>
            </HStack>
          </VStack>
        </Box>

        <JitsiMeetSDK
          jwt={meetingState.token}
          roomName={meetingState.config.roomName}
          displayName={meetingState.config.displayName}
          email={meetingState.config.email}
          startWithAudioMuted={meetingState.config.startWithAudioMuted}
          startWithVideoMuted={meetingState.config.startWithVideoMuted}
          onMeetingEnd={handleMeetingEnd}
          onParticipantJoined={handleParticipantJoined}
          onParticipantLeft={handleParticipantLeft}
          onRecordingStatusChanged={handleRecordingStatusChanged}
        />
      </Box>
    );
  }

  return (
    <Box minHeight="100vh" bg="gray.50" py={10}>
      <VStack spacing={8}>
        <Heading size="xl">Jitsi Meeting Test Page</Heading>

        <JitsiControls
          onJoinMeeting={handleJoinMeeting}
          isGeneratingToken={isGeneratingToken}
        />

        {debugInfo && (
          <Box
            maxWidth="800px"
            mx="auto"
            p={6}
            bg="white"
            borderRadius="md"
            boxShadow="md"
          >
            <VStack spacing={4} align="start">
              <HStack>
                <FaInfo />
                <Heading size="md">Debug Information</Heading>
              </HStack>
              <Box width="100%" overflow="auto">
                <Code
                  as="pre"
                  p={4}
                  borderRadius="md"
                  bg="gray.100"
                  fontSize="xs"
                  whiteSpace="pre-wrap"
                  wordBreak="break-word"
                >
                  {debugInfo}
                </Code>
              </Box>
            </VStack>
          </Box>
        )}

        {meetingState.type === "error" && (
          <Box
            maxWidth="600px"
            mx="auto"
            p={6}
            bg="white"
            borderRadius="md"
            boxShadow="md"
            borderColor="red.500"
            borderWidth={1}
          >
            <VStack spacing={3}>
              <Text color="red.500" fontWeight="bold">
                Error Initializing Meeting
              </Text>
              <Text>
                Please check your configuration and try again. Make sure the JWT
                keys are properly configured.
              </Text>
              <Button onClick={() => setMeetingState({ type: "idle" })}>
                Try Again
              </Button>
            </VStack>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
