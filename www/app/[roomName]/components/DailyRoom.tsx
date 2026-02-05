"use client";

import {
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Box, Spinner, Center, Text, Button, VStack } from "@chakra-ui/react";
import { useRouter, useParams } from "next/navigation";
import DailyIframe, {
  DailyCall,
  DailyCallOptions,
  DailyCustomTrayButton,
  DailyCustomTrayButtons,
  DailyEventObjectCustomButtonClick,
  DailyEventObjectFatalError,
  DailyFactoryOptions,
  DailyParticipantsObject,
} from "@daily-co/daily-js";
import type { components } from "../../reflector-api";
import { printApiError, ApiError } from "../../api/_error";
import { useAuth } from "../../lib/AuthProvider";
import { useConsentDialog } from "../../lib/consent";
import {
  useRoomJoinMeeting,
  useMeetingStartRecording,
} from "../../lib/apiHooks";
import { omit } from "remeda";
import {
  assertExists,
  NonEmptyString,
  parseNonEmptyString,
} from "../../lib/utils";
import { assertMeetingId, DailyRecordingType } from "../../lib/types";
import { useUuidV5 } from "react-uuid-hook";

const CONSENT_BUTTON_ID = "recording-consent";
const RECORDING_INDICATOR_ID = "recording-indicator";

// Namespace UUID for UUIDv5 generation of raw-tracks instanceIds
// DO NOT CHANGE: Breaks instanceId determinism across deployments
const RAW_TRACKS_NAMESPACE = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";

const RECORDING_START_DELAY_MS = 2000;
const RECORDING_START_MAX_RETRIES = 5;

type Meeting = components["schemas"]["Meeting"];
type Room = components["schemas"]["RoomDetails"];

type DailyRoomProps = {
  meeting: Meeting;
  room: Room;
};

const useCustomTrayButtons = (
  frame: {
    updateCustomTrayButtons: (
      customTrayButtons: DailyCustomTrayButtons,
    ) => void;
    joined: boolean;
  } | null,
) => {
  const [, setCustomTrayButtons] = useState<DailyCustomTrayButtons>({});
  return useCallback(
    (id: string, button: DailyCustomTrayButton | null) => {
      setCustomTrayButtons((prev) => {
        // would blink state when frame blinks but it's ok here
        const state =
          button === null ? omit(prev, [id]) : { ...prev, [id]: button };
        if (frame !== null && frame.joined)
          frame.updateCustomTrayButtons(state);
        return state;
      });
    },
    [setCustomTrayButtons, frame],
  );
};

const USE_FRAME_INIT_STATE = {
  frame: null as DailyCall | null,
  joined: false as boolean,
} as const;

type FatalError = { type: string; message: string };

// Daily js and not Daily react used right now because daily-js allows for prebuild interface vs. -react is customizable but has no nice defaults
const useFrame = (
  container: HTMLDivElement | null,
  cbs: {
    onLeftMeeting: () => void;
    onCustomButtonClick: (ev: DailyEventObjectCustomButtonClick) => void;
    onJoinMeeting: () => void;
    onError: (ev: DailyEventObjectFatalError) => void;
  },
) => {
  const [{ frame, joined }, setState] = useState(USE_FRAME_INIT_STATE);
  const setJoined = useCallback(
    (joined: boolean) => setState((prev) => ({ ...prev, joined })),
    [setState],
  );
  const setFrame = useCallback(
    (frame: DailyCall | null) => setState((prev) => ({ ...prev, frame })),
    [setState],
  );
  useEffect(() => {
    if (!container) return;
    const init = async () => {
      const existingFrame = DailyIframe.getCallInstance();
      if (existingFrame) {
        console.error("existing daily frame present");
        await existingFrame.destroy();
      }
      const frameOptions: DailyFactoryOptions = {
        iframeStyle: {
          width: "100vw",
          height: "100vh",
          border: "none",
        },
        showLeaveButton: true,
        showFullscreenButton: true,
      };
      const frame = DailyIframe.createFrame(container, frameOptions);
      setFrame(frame);
    };
    init().catch(
      console.error.bind(console, "Failed to initialize daily frame:"),
    );
    return () => {
      frame
        ?.destroy()
        .catch(console.error.bind(console, "Failed to destroy daily frame:"));
      setState(USE_FRAME_INIT_STATE);
    };
  }, [container]);
  useEffect(() => {
    if (!frame) return;
    frame.on("left-meeting", cbs.onLeftMeeting);
    frame.on("custom-button-click", cbs.onCustomButtonClick);
    frame.on("error", cbs.onError);
    const joinCb = () => {
      if (!frame) {
        console.error("frame is null in joined-meeting callback");
        return;
      }
      cbs.onJoinMeeting();
    };
    frame.on("joined-meeting", joinCb);
    return () => {
      frame.off("left-meeting", cbs.onLeftMeeting);
      frame.off("custom-button-click", cbs.onCustomButtonClick);
      frame.off("error", cbs.onError);
      frame.off("joined-meeting", joinCb);
    };
  }, [frame, cbs]);
  const frame_ = useMemo(() => {
    if (frame === null) return frame;
    return {
      join: async (
        properties?: DailyCallOptions,
      ): Promise<DailyParticipantsObject | void> => {
        await frame.join(properties);
        setJoined(!frame.isDestroyed());
      },
      updateCustomTrayButtons: (
        customTrayButtons: DailyCustomTrayButtons,
      ): DailyCall => frame.updateCustomTrayButtons(customTrayButtons),
    };
  }, [frame]);
  const setCustomTrayButton = useCustomTrayButtons(
    useMemo(() => {
      if (frame_ === null) return null;
      return {
        updateCustomTrayButtons: frame_.updateCustomTrayButtons,
        joined,
      };
    }, [frame_, joined]),
  );
  return [
    frame_,
    {
      setCustomTrayButton,
    },
  ] as const;
};

export default function DailyRoom({ meeting, room }: DailyRoomProps) {
  const router = useRouter();
  const params = useParams();
  const auth = useAuth();
  const authLastUserId = auth.lastUserId;
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const joinMutation = useRoomJoinMeeting();
  const startRecordingMutation = useMeetingStartRecording();
  const [joinedMeeting, setJoinedMeeting] = useState<Meeting | null>(null);
  const [fatalError, setFatalError] = useState<FatalError | null>(null);
  const fatalErrorRef = useRef<FatalError | null>(null);

  // Generate deterministic instanceIds so all participants use SAME IDs
  const cloudInstanceId = parseNonEmptyString(meeting.id);
  const rawTracksInstanceId = parseNonEmptyString(
    useUuidV5(meeting.id, RAW_TRACKS_NAMESPACE)[0],
  );

  const roomName = params?.roomName as string;

  const {
    showConsentModal,
    showRecordingIndicator: showRecordingInTray,
    showConsentButton,
  } = useConsentDialog({
    meetingId: assertMeetingId(meeting.id),
    recordingType: meeting.recording_type,
    skipConsent: room.skip_consent,
  });
  const showConsentModalRef = useRef(showConsentModal);
  showConsentModalRef.current = showConsentModal;

  useEffect(() => {
    if (authLastUserId === undefined || !meeting?.id || !roomName) return;

    const join = async () => {
      try {
        const result = await joinMutation.mutateAsync({
          params: {
            path: {
              room_name: roomName,
              meeting_id: meeting.id,
            },
          },
        });
        setJoinedMeeting(result);
      } catch (error) {
        console.error("Failed to join meeting:", error);
      }
    };

    join().catch(console.error.bind(console, "Failed to join meeting:"));
  }, [meeting?.id, roomName, authLastUserId]);

  const roomUrl = joinedMeeting?.room_url;

  const handleLeave = useCallback(() => {
    // If a fatal error occurred, don't redirect — let the error UI show
    if (fatalErrorRef.current) return;
    router.push("/browse");
  }, [router]);

  const handleError = useCallback((ev: DailyEventObjectFatalError) => {
    const error: FatalError = {
      type: ev.error?.type ?? "unknown",
      message: ev.errorMsg,
    };
    fatalErrorRef.current = error;
    setFatalError(error);
  }, []);

  const handleCustomButtonClick = useCallback(
    (ev: DailyEventObjectCustomButtonClick) => {
      if (ev.button_id === CONSENT_BUTTON_ID) {
        showConsentModalRef.current();
      }
    },
    [
      /*keep static; iframe recreation depends on it*/
    ],
  );

  const handleFrameJoinMeeting = useCallback(() => {
    if (meeting.recording_type === "cloud") {
      console.log("Starting dual recording via REST API", {
        cloudInstanceId,
        rawTracksInstanceId,
      });

      // Start both cloud and raw-tracks via backend REST API (with retry on 404)
      // Daily.co needs time to register call as "hosting" for REST API
      const startRecordingWithRetry = (
        type: DailyRecordingType,
        instanceId: NonEmptyString,
        attempt: number = 1,
      ) => {
        setTimeout(() => {
          startRecordingMutation.mutate(
            {
              params: {
                path: {
                  meeting_id: meeting.id,
                },
              },
              body: {
                type,
                instanceId,
              },
            },
            {
              onError: (error: any) => {
                const errorText = error?.detail || error?.message || "";
                const is404NotHosting = errorText.includes(
                  "does not seem to be hosting a call",
                );
                const isActiveStream = errorText.includes(
                  "has an active stream",
                );

                if (is404NotHosting && attempt < RECORDING_START_MAX_RETRIES) {
                  console.log(
                    `${type}: Call not hosting yet, retry ${attempt + 1}/${RECORDING_START_MAX_RETRIES} in ${RECORDING_START_DELAY_MS}ms...`,
                  );
                  startRecordingWithRetry(type, instanceId, attempt + 1);
                } else if (isActiveStream) {
                  console.log(
                    `${type}: Recording already active (started by another participant)`,
                  );
                } else {
                  console.error(`Failed to start ${type} recording:`, error);
                }
              },
            },
          );
        }, RECORDING_START_DELAY_MS);
      };

      // Start both recordings
      startRecordingWithRetry("cloud", cloudInstanceId);
      startRecordingWithRetry("raw-tracks", rawTracksInstanceId);
    }
  }, [
    meeting.recording_type,
    meeting.id,
    startRecordingMutation,
    cloudInstanceId,
    rawTracksInstanceId,
  ]);

  const recordingIconUrl = useMemo(
    () => new URL("/recording-icon.svg", window.location.origin),
    [],
  );

  const [frame, { setCustomTrayButton }] = useFrame(container, {
    onLeftMeeting: handleLeave,
    onCustomButtonClick: handleCustomButtonClick,
    onJoinMeeting: handleFrameJoinMeeting,
    onError: handleError,
  });

  useEffect(() => {
    if (!frame || !roomUrl) return;
    frame
      .join({
        url: roomUrl,
        sendSettings: {
          video: {
            // Optimize bandwidth for camera video
            // allowAdaptiveLayers automatically adjusts quality based on network conditions
            allowAdaptiveLayers: true,
            // Use bandwidth-optimized preset as fallback for browsers without adaptive support
            maxQuality: "medium",
          },
          // Note: screenVideo intentionally not configured to preserve full quality for screen shares
        },
      })
      .catch(console.error.bind(console, "Failed to join daily room:"));
  }, [frame, roomUrl]);

  useEffect(() => {
    setCustomTrayButton(
      RECORDING_INDICATOR_ID,
      showRecordingInTray
        ? {
            iconPath: recordingIconUrl.href,
            label: "Recording",
            tooltip: "Recording in progress",
          }
        : null,
    );
  }, [showRecordingInTray, recordingIconUrl, setCustomTrayButton]);

  useEffect(() => {
    setCustomTrayButton(
      CONSENT_BUTTON_ID,
      showConsentButton
        ? {
            iconPath: recordingIconUrl.href,
            label: "Recording (click to consent)",
            tooltip: "Recording (click to consent)",
          }
        : null,
    );
  }, [showConsentButton, recordingIconUrl, setCustomTrayButton]);

  if (authLastUserId === undefined) {
    return (
      <Center width="100vw" height="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (joinMutation.isError) {
    const apiDetail = printApiError(joinMutation.error as ApiError);
    return (
      <Center width="100vw" height="100vh">
        <VStack gap={4}>
          <Text color="red.500">
            {apiDetail ?? "Failed to join meeting. Please try again."}
          </Text>
          <Button onClick={() => router.push(`/${roomName}`)}>
            Back to Room
          </Button>
        </VStack>
      </Center>
    );
  }

  if (fatalError) {
    const renderFatalError = () => {
      switch (fatalError.type) {
        case "connection-error":
          return (
            <VStack gap={4}>
              <Text color="red.500">
                Connection lost. Please check your network.
              </Text>
              <Button onClick={() => window.location.reload()}>
                Try Rejoining
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push(`/${roomName}`)}
              >
                Leave
              </Button>
            </VStack>
          );
        case "exp-room":
          return (
            <VStack gap={4}>
              <Text color="red.500">The meeting time has ended.</Text>
              <Button onClick={() => router.push(`/${roomName}`)}>
                Back to Room
              </Button>
            </VStack>
          );
        case "ejected":
          return (
            <VStack gap={4}>
              <Text color="red.500">You were removed from this meeting.</Text>
              <Button onClick={() => router.push(`/${roomName}`)}>
                Back to Room
              </Button>
            </VStack>
          );
        default:
          return (
            <VStack gap={4}>
              <Text color="red.500">
                Something went wrong: {fatalError.message}
              </Text>
              <Button onClick={() => router.push(`/${roomName}`)}>
                Back to Room
              </Button>
            </VStack>
          );
      }
    };
    return (
      <Center width="100vw" height="100vh">
        {renderFatalError()}
      </Center>
    );
  }

  if (!roomUrl) {
    return null;
  }

  return (
    <Box position="relative" width="100vw" height="100vh">
      <div ref={setContainer} style={{ width: "100%", height: "100%" }} />
    </Box>
  );
}
