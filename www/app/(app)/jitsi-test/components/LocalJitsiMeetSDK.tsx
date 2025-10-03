"use client";

import { useCallback, useRef, useEffect } from "react";
import { JitsiMeeting } from "@jitsi/react-sdk";
import { Box } from "@chakra-ui/react";
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

interface LocalJitsiMeetSDKProps {
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

// Event collector URL - change this to match your Docker setup
const EVENT_COLLECTOR_URL =
  process.env.NEXT_PUBLIC_EVENT_COLLECTOR_URL || "http://localhost:3002";
const JITSI_DOMAIN = process.env.NEXT_PUBLIC_JITSI_DOMAIN || "jitsi.local";

// Send events to our event collector
async function sendEventToCollector(type: string, roomName: string, data: any) {
  try {
    await fetch(`${EVENT_COLLECTOR_URL}/webhook/client`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type,
        roomName,
        data,
        metadata: {
          timestamp: new Date().toISOString(),
          source: "frontend",
        },
      }),
    });
  } catch (error) {
    console.error("Failed to send event to collector:", error);
  }
}

export default function LocalJitsiMeetSDK({
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
}: LocalJitsiMeetSDKProps): JSX.Element {
  const apiRef = useRef<JitsiMeetExternalAPI | null>(null);

  // Check recording status periodically
  useEffect(() => {
    const checkRecordingStatus = async () => {
      if (!roomName) return;

      try {
        const response = await fetch(
          `${EVENT_COLLECTOR_URL}/events/${roomName}`,
        );
        const data = await response.json();

        const recordingEvents = data.events.filter(
          (e: any) =>
            e.type === "recording_started" || e.type === "recording_stopped",
        );

        if (recordingEvents.length > 0) {
          const latestRecording = recordingEvents[0];
          console.log("📹 Latest recording event:", latestRecording);
        }
      } catch (error) {
        console.error("Failed to check recording status:", error);
      }
    };

    // Check every 5 seconds
    const interval = setInterval(checkRecordingStatus, 5000);
    checkRecordingStatus(); // Initial check

    return () => clearInterval(interval);
  }, [roomName]);

  const handleApiReady = useCallback(
    (externalApi: JitsiMeetExternalAPI) => {
      apiRef.current = externalApi;

      console.log("🎯 Local Jitsi API Ready");
      sendEventToCollector("api_ready", roomName, { displayName });

      // Add comprehensive event listeners
      externalApi.addListener("readyToClose", () => {
        sendEventToCollector("ready_to_close", roomName, {});
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
          sendEventToCollector("participant_joined", roomName, { participant });
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
          sendEventToCollector("participant_left", roomName, { participant });
          if (onParticipantLeft) {
            onParticipantLeft(participant);
          }
        },
      );

      externalApi.addListener(
        "videoConferenceJoined",
        (event: JitsiVideoConferenceEvent) => {
          sendEventToCollector("videoConferenceJoined", roomName, event);

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
                Successfully joined the meeting on local Jitsi
              </Box>
            ),
          });

          // Try to start recording after joining
          console.log("🎬 Attempting to start recording...");
          try {
            externalApi.executeCommand("startRecording", {
              mode: "file",
              shouldShare: false,
            });
          } catch (error) {
            console.error("Failed to start recording:", error);
          }
        },
      );

      externalApi.addListener("videoConferenceLeft", () => {
        sendEventToCollector("videoConferenceLeft", roomName, {});
      });

      externalApi.addListener(
        "recordingStatusChanged",
        (event: JitsiRecordingEvent) => {
          const status: JitsiRecordingStatus = {
            on: event.on,
            mode: event.mode,
          };

          sendEventToCollector("recording_status_changed", roomName, {
            status,
          });

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
                {status.on ? "🔴 Recording started" : "⏹️ Recording stopped"}
              </Box>
            ),
          });
        },
      );

      externalApi.addListener("errorOccurred", (error: JitsiErrorEvent) => {
        console.error("Jitsi error:", error);
        sendEventToCollector("error_occurred", roomName, { error });
        if (onError) {
          onError(new Error(error.message || "Unknown Jitsi error"));
        }
      });

      // Log all events for debugging
      const allEvents = [
        "audioAvailabilityChanged",
        "audioMuteStatusChanged",
        "videoAvailabilityChanged",
        "videoMuteStatusChanged",
        "screenSharingStatusChanged",
        "tileViewChanged",
        "chatUpdated",
        "incomingMessage",
        "outgoingMessage",
        "dominantSpeakerChanged",
        "raiseHandUpdated",
      ];

      allEvents.forEach((eventName) => {
        externalApi.addListener(eventName, (data: any) => {
          console.log(`📡 Local Jitsi Event: ${eventName}`, data);
          sendEventToCollector(eventName, roomName, data);
        });
      });
    },
    [
      roomName,
      displayName,
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
    enableInsecureRoomNameWarning: false,
    // Important: Enable recording
    recordingService: {
      enabled: true,
      mode: "file",
    },
    // Disable some features for local testing
    analytics: {
      disabled: true,
    },
    p2p: {
      enabled: false,
    },
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

  return (
    <Box width="100%" height="100vh">
      <Box
        position="absolute"
        top="10px"
        right="10px"
        bg="blue.500"
        color="white"
        px={3}
        py={1}
        borderRadius="md"
        fontSize="sm"
        zIndex={100}
      >
        🏠 Local Jitsi: {JITSI_DOMAIN}
      </Box>
      <JitsiMeeting
        domain={JITSI_DOMAIN}
        roomName={roomName}
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
