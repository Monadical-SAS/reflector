"use client";

import {
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Box, Spinner, Center, Text } from "@chakra-ui/react";
import { useRouter, useParams } from "next/navigation";
import DailyIframe, {
  DailyCall,
  DailyCallOptions,
  DailyCustomTrayButton,
  DailyCustomTrayButtons,
  DailyEventObjectCustomButtonClick,
  DailyFactoryOptions,
  DailyParticipantsObject,
} from "@daily-co/daily-js";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import {
  recordingTypeRequiresConsent,
  useConsentDialog,
} from "../../lib/consent";
import { useRoomJoinMeeting } from "../../lib/apiHooks";
import { omit } from "remeda";
import { assertExists } from "../../lib/utils";

const CONSENT_BUTTON_ID = "recording-consent";
const RECORDING_INDICATOR_ID = "recording-indicator";

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

// Daily js and not Daily react used right now because daily-js allows for prebuild interface vs. -react is customizable but has no nice defaults
const useFrame = (
  container: HTMLDivElement | null,
  cbs: {
    onLeftMeeting: () => void;
    onCustomButtonClick: (ev: DailyEventObjectCustomButtonClick) => void;
    onJoinMeeting: (
      startRecording: (args: { type: "raw-tracks" }) => void,
    ) => void;
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
    const joinCb = () => {
      if (!frame) {
        console.error("frame is null in joined-meeting callback");
        return;
      }
      cbs.onJoinMeeting(frame.startRecording.bind(frame));
    };
    frame.on("joined-meeting", joinCb);
    return () => {
      frame.off("left-meeting", cbs.onLeftMeeting);
      frame.off("custom-button-click", cbs.onCustomButtonClick);
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
    setFrame,
    {
      joined,
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
  const [joinedMeeting, setJoinedMeeting] = useState<Meeting | null>(null);

  const roomName = params?.roomName as string;

  const showRecordingInTray =
    meeting.recording_type &&
    recordingTypeRequiresConsent(meeting.recording_type) &&
    // users know about recording in case of no-skip-consent from the consent dialog
    room.skip_consent;

  const needsConsent =
    meeting.recording_type &&
    recordingTypeRequiresConsent(meeting.recording_type) &&
    !room.skip_consent;
  const { showConsentModal, consentState, hasConsent } = useConsentDialog(
    meeting.id,
  );
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
    router.push("/browse");
  }, [router]);

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

  const handleFrameJoinMeeting = useCallback(
    (startRecording: (args: { type: "raw-tracks" }) => void) => {
      try {
        if (meeting.recording_type === "cloud") {
          console.log("Starting cloud recording");
          startRecording({ type: "raw-tracks" });
        }
      } catch (error) {
        console.error("Failed to start recording:", error);
      }
    },
    [meeting.recording_type],
  );

  const recordingIconUrl = useMemo(
    () => new URL("/recording-icon.svg", window.location.origin),
    [],
  );

  const [frame, setFrame, { setCustomTrayButton }] = useFrame(container, {
    onLeftMeeting: handleLeave,
    onCustomButtonClick: handleCustomButtonClick,
    onJoinMeeting: handleFrameJoinMeeting,
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

  /*
       if (needsConsent && !hasConsent(meeting.id)) {
          const iconUrl = new URL("/consent-icon.svg", window.location.origin);
          frameOptions.customTrayButtons = {
            [CONSENT_BUTTON_ID]: {
              iconPath: iconUrl.href,
              label: "Consent",
              tooltip: "Recording consent - click to respond",
            },
          };
        }
   */

  if (authLastUserId === undefined) {
    return (
      <Center width="100vw" height="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (joinMutation.isError) {
    return (
      <Center width="100vw" height="100vh">
        <Text color="red.500">Failed to join meeting. Please try again.</Text>
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
