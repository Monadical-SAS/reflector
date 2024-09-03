"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef } from "react";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

export default function Room(details: RoomDetails) {
  const wherebyRef = useRef<HTMLElement>(null);
  const roomName = details.params.roomName;
  const meeting = useRoomMeeting(roomName);
  const router = useRouter();
  const { status } = useSession();
  const sessionReady = status !== "loading";
  const isAuthenticated = status === "authenticated";

  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const handleLeave = useCallback((e) => {
    router.push("/browse");
  }, []);

  useEffect(() => {
    if (!sessionReady || !isAuthenticated || !roomUrl) return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, roomUrl]);

  return (
    <>
      {roomUrl && (
        <whereby-embed
          ref={wherebyRef}
          room={roomUrl}
          style={{ width: "100vw", height: "100vh" }}
        />
      )}
    </>
  );
}
