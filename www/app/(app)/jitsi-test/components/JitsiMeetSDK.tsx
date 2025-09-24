"use client";

import { useCallback, useRef } from "react";
import { JaaSMeeting } from "@jitsi/react-sdk";
import { Box } from "@chakra-ui/react";
import { getAppId } from "../utils/jitsiConfig";
import {
  JitsiParticipant,
  JitsiRecordingStatus,
  JitsiMeetExternalAPI,
  JitsiParticipantEvent,
  JitsiRecordingEvent,
  JitsiVideoConferenceEvent,
  JitsiErrorEvent,
} from "../utils/types";
import { toaster } from "../../../components/ui/toaster";

interface JitsiMeetSDKProps {
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

export default function JitsiMeetSDK({
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
}: JitsiMeetSDKProps): JSX.Element {
  const apiRef = useRef<JitsiMeetExternalAPI | null>(null);

  const handleApiReady = useCallback(
    (externalApi: JitsiMeetExternalAPI) => {
      apiRef.current = externalApi;

      // Add event listeners
      externalApi.addListener("readyToClose", () => {
        if (onMeetingEnd) {
          onMeetingEnd();
        }
      });

      externalApi.addListener(
        "participantJoined",
        (event: JitsiParticipantEvent) => {
          const participant: JitsiParticipant = {
            id: event.id,
            displayName: event.displayName || "Guest",
          };
          if (onParticipantJoined) {
            onParticipantJoined(participant);
          }
        },
      );

      externalApi.addListener(
        "participantLeft",
        (event: JitsiParticipantEvent) => {
          const participant: JitsiParticipant = {
            id: event.id,
            displayName: event.displayName || "Guest",
          };
          if (onParticipantLeft) {
            onParticipantLeft(participant);
          }
        },
      );

      externalApi.addListener(
        "videoConferenceJoined",
        (event: JitsiVideoConferenceEvent) => {
          toaster.create({
            placement: "top",
            duration: 3000,
            render: () => (
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
                Successfully joined the meeting
              </Box>
            ),
          });
        },
      );

      externalApi.addListener(
        "recordingStatusChanged",
        (event: JitsiRecordingEvent) => {
          const status: JitsiRecordingStatus = {
            on: event.on,
            mode: event.mode,
          };
          if (onRecordingStatusChanged) {
            onRecordingStatusChanged(status);
          }

          toaster.create({
            placement: "top",
            duration: 3000,
            render: () => (
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
                {status.on ? "Recording started" : "Recording stopped"}
              </Box>
            ),
          });
        },
      );

      externalApi.addListener("errorOccurred", (error: JitsiErrorEvent) => {
        console.error("Jitsi error:", error);
        if (onError) {
          onError(new Error(error.message || "Unknown Jitsi error"));
        }
      });
    },
    [
      onMeetingEnd,
      onParticipantJoined,
      onParticipantLeft,
      onRecordingStatusChanged,
      onError,
    ],
  );

  const handleReadyToClose = useCallback(() => {
    if (onMeetingEnd) {
      onMeetingEnd();
    }
  }, [onMeetingEnd]);

  const configOverwrite = {
    startWithAudioMuted,
    startWithVideoMuted,
    disableModeratorIndicator: false,
    enableEmailInStats: true,
    prejoinPageEnabled: false,
    disableDeepLinking: true,
    transcribingEnabled: false,
    liveStreamingEnabled: false,
    fileRecordingsEnabled: true,
    requireDisplayName: false,
  };

  const interfaceConfigOverwrite = {
    TOOLBAR_BUTTONS: [
      "microphone",
      "camera",
      "desktop",
      "fullscreen",
      "recording",
      "chat",
      "settings",
      "hangup",
      "participants-pane",
      "stats",
      "tileview",
      "filmstrip",
    ],
    TOOLBAR_ALWAYS_VISIBLE: false,
    SHOW_JITSI_WATERMARK: false,
    SHOW_WATERMARK_FOR_GUESTS: false,
    DISABLE_VIDEO_BACKGROUND: false,
    MOBILE_APP_PROMO: false,
    HIDE_INVITE_MORE_HEADER: true,
  };

  const userInfo = {
    displayName,
    email,
  };

  // Get the app ID from environment
  let appId: string;
  try {
    appId = getAppId();
  } catch (error) {
    console.error("Failed to get app ID:", error);
    if (onError) {
      onError(new Error("Jitsi configuration error"));
    }
    return <Box>Error: Jitsi not configured</Box>;
  }

  return (
    <Box width="100%" height="100vh">
      <JaaSMeeting
        appId={appId}
        roomName={roomName}
        jwt={jwt}
        configOverwrite={configOverwrite}
        interfaceConfigOverwrite={interfaceConfigOverwrite}
        userInfo={userInfo}
        onApiReady={handleApiReady}
        onReadyToClose={handleReadyToClose}
        getIFrameRef={(iframeRef) => {
          if (iframeRef) {
            iframeRef.style.height = "100vh";
            iframeRef.style.width = "100%";
          }
        }}
      />
    </Box>
  );
}
