"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Spinner } from "@chakra-ui/react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";
import VideoPlatformEmbed from "../lib/videoPlatforms/VideoPlatformEmbed";

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

export default function Room(details: RoomDetails) {
  const [platformReady, setPlatformReady] = useState(false);
  const roomName = details.params.roomName;
  const meeting = useRoomMeeting(roomName);
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  const handlePlatformReady = useCallback(() => {
    setPlatformReady(true);
  }, []);

  useEffect(() => {
    if (
      !isLoading &&
      meeting?.error &&
      "status" in meeting.error &&
      meeting.error.status === 404
    ) {
      notFound();
    }
  }, [isLoading, meeting?.error]);

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
        <Spinner color="blue.500" size="xl" />
      </Box>
    );
  }

  if (!meeting?.response || !isAuthenticated) {
    return null;
  }

  return (
    <VideoPlatformEmbed
      meeting={meeting.response}
      onLeave={handleLeave}
      onReady={handlePlatformReady}
    />
  );
}
