"use client";

import { useCallback, useEffect, useRef } from "react";
import { Box } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import DailyIframe, { DailyCall } from "@daily-co/daily-js";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import {
  ConsentDialogButton,
  recordingTypeRequiresConsent,
} from "../../lib/consent";

type Meeting = components["schemas"]["Meeting"];

interface DailyRoomProps {
  meeting: Meeting;
}

export default function DailyRoom({ meeting }: DailyRoomProps) {
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const containerRef = useRef<HTMLDivElement>(null);

  const roomUrl = meeting?.host_room_url || meeting?.room_url;

  const isLoading = status === "loading";

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (isLoading || !roomUrl || !containerRef.current) return;

    let frame: DailyCall | null = null;
    let destroyed = false;

    const createAndJoin = async () => {
      try {
        const existingFrame = DailyIframe.getCallInstance();
        if (existingFrame) {
          await existingFrame.destroy();
        }

        frame = DailyIframe.createFrame(containerRef.current!, {
          iframeStyle: {
            width: "100vw",
            height: "100vh",
            border: "none",
          },
          showLeaveButton: true,
          showFullscreenButton: true,
        });

        if (destroyed) {
          await frame.destroy();
          return;
        }

        frame.on("left-meeting", handleLeave);
        await frame.join({ url: roomUrl });
      } catch (error) {
        console.error("Error creating Daily frame:", error);
      }
    };

    createAndJoin();

    return () => {
      destroyed = true;
      if (frame) {
        frame.destroy().catch((e) => {
          console.error("Error destroying frame:", e);
        });
      }
    };
  }, [roomUrl, isLoading, handleLeave]);

  if (!roomUrl) {
    return null;
  }

  return (
    <Box position="relative" width="100vw" height="100vh">
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {meeting.recording_type &&
        recordingTypeRequiresConsent(meeting.recording_type) &&
        meeting.id && <ConsentDialogButton meetingId={meeting.id} />}
    </Box>
  );
}
