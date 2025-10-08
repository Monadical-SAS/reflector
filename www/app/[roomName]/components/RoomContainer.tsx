"use client";

import { Suspense } from "react";
import { Box, Spinner } from "@chakra-ui/react";
import WherebyRoom from "./WherebyRoom";
import DailyRoom from "./DailyRoom";
import useRoomMeeting from "../useRoomMeeting";

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

function LoadingSpinner() {
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

export default function RoomContainer({ params }: RoomDetails) {
  const roomName = params.roomName;
  const meeting = useRoomMeeting(roomName);

  if (meeting.loading) {
    return <LoadingSpinner />;
  }

  if (meeting.error || !meeting.response) {
    return <LoadingSpinner />;
  }

  const platform = meeting.response.platform || "whereby";

  if (platform === "daily") {
    return <DailyRoom meeting={meeting.response} />;
  }

  // Default to Whereby for backward compatibility
  return <WherebyRoom meeting={meeting.response} />;
}
