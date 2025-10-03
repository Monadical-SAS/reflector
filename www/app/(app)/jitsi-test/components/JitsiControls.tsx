"use client";

import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Switch,
  Heading,
  Badge,
  Separator,
  IconButton,
  Field,
} from "@chakra-ui/react";
import { useState, useCallback, FormEvent, ChangeEvent } from "react";
import { MeetingConfig } from "../utils/types";
import { generateRoomName } from "../utils/jwtGenerator";
import { FaRandom, FaCopy } from "react-icons/fa";
import { toaster } from "../../../components/ui/toaster";
import {
  isValidRoomName,
  isValidDisplayName,
  isValidEmail,
  getRoomNameError,
} from "../utils/validation";

interface JitsiControlsProps {
  onJoinMeeting: (config: MeetingConfig) => void;
  isGeneratingToken?: boolean;
}

export default function JitsiControls({
  onJoinMeeting,
  isGeneratingToken = false,
}: JitsiControlsProps): JSX.Element {
  const [roomName, setRoomName] = useState<string>("");
  const [displayName, setDisplayName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [isModerator, setIsModerator] = useState<boolean>(true);
  const [startWithAudioMuted, setStartWithAudioMuted] = useState<boolean>(true);
  const [startWithVideoMuted, setStartWithVideoMuted] = useState<boolean>(true);
  const [enableRecording, setEnableRecording] = useState<boolean>(true);
  const [enableTranscription, setEnableTranscription] = useState<boolean>(true);
  const [enableLivestreaming, setEnableLivestreaming] =
    useState<boolean>(false);

  const [validationErrors, setValidationErrors] = useState<{
    roomName?: string;
    displayName?: string;
    email?: string;
  }>({});

  const generateRandomRoom = useCallback(() => {
    const newRoomName = generateRoomName("reflector");
    setRoomName(newRoomName);
    setValidationErrors((prev) => ({ ...prev, roomName: undefined }));
  }, []);

  const copyRoomName = useCallback(() => {
    if (roomName) {
      navigator.clipboard.writeText(roomName);
      toaster.create({
        placement: "top",
        duration: 2000,
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
            <Text>Room name copied to clipboard</Text>
          </Box>
        ),
      });
    }
  }, [roomName]);

  const validateForm = useCallback((): boolean => {
    const errors: typeof validationErrors = {};

    // Use centralized validation utilities
    const roomNameError = getRoomNameError(roomName.trim());
    if (roomNameError) {
      errors.roomName = roomNameError;
    }

    if (!isValidDisplayName(displayName.trim())) {
      errors.displayName = "Display name is required";
    }

    if (email && !isValidEmail(email.trim())) {
      errors.email = "Invalid email format";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [roomName, displayName, email]);

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      if (!validateForm()) {
        return;
      }

      const config: MeetingConfig = {
        roomName: roomName.trim(),
        displayName: displayName.trim(),
        email: email.trim() || undefined,
        isModerator,
        startWithAudioMuted,
        startWithVideoMuted,
        enableRecording,
        enableTranscription,
        enableLivestreaming,
      };

      onJoinMeeting(config);
    },
    [
      roomName,
      displayName,
      email,
      isModerator,
      startWithAudioMuted,
      startWithVideoMuted,
      enableRecording,
      enableTranscription,
      enableLivestreaming,
      validateForm,
      onJoinMeeting,
    ],
  );

  const handleRoomNameChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      setRoomName(e.target.value);
      if (validationErrors.roomName) {
        setValidationErrors((prev) => ({ ...prev, roomName: undefined }));
      }
    },
    [validationErrors.roomName],
  );

  const handleDisplayNameChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      setDisplayName(e.target.value);
      if (validationErrors.displayName) {
        setValidationErrors((prev) => ({ ...prev, displayName: undefined }));
      }
    },
    [validationErrors.displayName],
  );

  const handleEmailChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      setEmail(e.target.value);
      if (validationErrors.email) {
        setValidationErrors((prev) => ({ ...prev, email: undefined }));
      }
    },
    [validationErrors.email],
  );

  return (
    <Box maxWidth="600px" mx="auto" p={6}>
      <Box bg="white" borderRadius="md" boxShadow="md" p={6}>
        <VStack spacing={6} as="form" onSubmit={handleSubmit}>
          <Heading size="lg">Join Jitsi Meeting</Heading>

          <Field.Root invalid={!!validationErrors.roomName}>
            <Field.Label>Room Name</Field.Label>
            <HStack>
              <Input
                placeholder="Enter room name"
                value={roomName}
                onChange={handleRoomNameChange}
                disabled={isGeneratingToken}
              />
              <IconButton
                aria-label="Generate random room"
                onClick={generateRandomRoom}
                disabled={isGeneratingToken}
                title="Generate random room name"
              >
                <FaRandom />
              </IconButton>
              <IconButton
                aria-label="Copy room name"
                onClick={copyRoomName}
                disabled={!roomName || isGeneratingToken}
                title="Copy room name"
              >
                <FaCopy />
              </IconButton>
            </HStack>
            {validationErrors.roomName && (
              <Field.ErrorText>{validationErrors.roomName}</Field.ErrorText>
            )}
          </Field.Root>

          <Field.Root invalid={!!validationErrors.displayName}>
            <Field.Label>Display Name</Field.Label>
            <Input
              placeholder="Enter your name"
              value={displayName}
              onChange={handleDisplayNameChange}
              disabled={isGeneratingToken}
            />
            {validationErrors.displayName && (
              <Field.ErrorText>{validationErrors.displayName}</Field.ErrorText>
            )}
          </Field.Root>

          <Field.Root invalid={!!validationErrors.email}>
            <Field.Label>Email (Optional)</Field.Label>
            <Input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={handleEmailChange}
              disabled={isGeneratingToken}
            />
            {validationErrors.email && (
              <Field.ErrorText>{validationErrors.email}</Field.ErrorText>
            )}
          </Field.Root>

          <Separator />

          <VStack spacing={4} width="100%">
            <Heading size="md">Meeting Settings</Heading>

            <HStack justifyContent="space-between" width="100%">
              <Text>Join as Moderator</Text>
              <Switch.Root
                checked={isModerator}
                onCheckedChange={(e) => setIsModerator(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>

            <HStack justifyContent="space-between" width="100%">
              <Text>Start with Audio Muted</Text>
              <Switch.Root
                checked={startWithAudioMuted}
                onCheckedChange={(e) => setStartWithAudioMuted(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>

            <HStack justifyContent="space-between" width="100%">
              <Text>Start with Video Muted</Text>
              <Switch.Root
                checked={startWithVideoMuted}
                onCheckedChange={(e) => setStartWithVideoMuted(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>
          </VStack>

          <Separator />

          <VStack spacing={4} width="100%">
            <Heading size="md">Features</Heading>

            <HStack justifyContent="space-between" width="100%">
              <HStack>
                <Text>Recording</Text>
                {enableRecording && <Badge colorScheme="green">Enabled</Badge>}
              </HStack>
              <Switch.Root
                checked={enableRecording}
                onCheckedChange={(e) => setEnableRecording(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>

            <HStack justifyContent="space-between" width="100%">
              <HStack>
                <Text>Transcription</Text>
                {enableTranscription && (
                  <Badge colorScheme="blue">Enabled</Badge>
                )}
              </HStack>
              <Switch.Root
                checked={enableTranscription}
                onCheckedChange={(e) => setEnableTranscription(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>

            <HStack justifyContent="space-between" width="100%">
              <HStack>
                <Text>Livestreaming</Text>
                {enableLivestreaming && (
                  <Badge colorScheme="purple">Enabled</Badge>
                )}
              </HStack>
              <Switch.Root
                checked={enableLivestreaming}
                onCheckedChange={(e) => setEnableLivestreaming(!!e.checked)}
                disabled={isGeneratingToken}
              >
                <Switch.HiddenInput />
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </HStack>
          </VStack>

          <Button
            type="submit"
            colorScheme="blue"
            size="lg"
            width="100%"
            disabled={isGeneratingToken}
          >
            {isGeneratingToken ? "Generating token..." : "Join Meeting"}
          </Button>
        </VStack>
      </Box>
    </Box>
  );
}
