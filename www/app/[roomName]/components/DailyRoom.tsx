"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Spinner, Center, Text } from "@chakra-ui/react";
import { useRouter, useParams } from "next/navigation";
import DailyIframe, { DailyCall } from "@daily-co/daily-js";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import {
  ConsentDialogButton,
  recordingTypeRequiresConsent,
} from "../../lib/consent";
import { useRoomJoinMeeting } from "../../lib/apiHooks";

type Meeting = components["schemas"]["Meeting"];

interface DailyRoomProps {
  meeting: Meeting;
}

export default function DailyRoom({ meeting }: DailyRoomProps) {
  const router = useRouter();
  const params = useParams();
  const auth = useAuth();
  const status = auth.status;
  const containerRef = useRef<HTMLDivElement>(null);
  const joinMutation = useRoomJoinMeeting();
  const [joinedMeeting, setJoinedMeeting] = useState<Meeting | null>(null);

  const roomName = params?.roomName as string;

  // Always call /join to get a fresh token with user_id
  useEffect(() => {
    if (status === "loading" || !meeting?.id || !roomName) return;

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

    join();
  }, [meeting?.id, roomName, status]);

  const roomUrl = joinedMeeting?.host_room_url || joinedMeeting?.room_url;
  const isLoading =
    status === "loading" || joinMutation.isPending || !joinedMeeting;

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

        frame.on("joined-meeting", async () => {
          try {
            await frame.startRecording({ type: "raw-tracks" });
          } catch (error) {
            console.error("Failed to start recording:", error);
          }
        });

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

  if (isLoading) {
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
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {meeting.recording_type &&
        recordingTypeRequiresConsent(meeting.recording_type) &&
        meeting.id && <ConsentDialogButton meetingId={meeting.id} />}
    </Box>
  );
}
