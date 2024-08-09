"use client";

import "@whereby.com/browser-sdk/embed";
import { useCallback, useEffect, useRef } from "react";
import useTranscript from "../../useTranscript";
import useMeeting from "../../useMeeting";

export type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptMeeting(details: TranscriptDetails) {
  const wherebyRef = useRef<HTMLElement>(null);

  const transcript = useTranscript(details.params.transcriptId);
  const meeting = useMeeting(transcript?.response?.meeting_id);
  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const handleLeave = useCallback((event) => {
    console.log("LEFT", event);
  }, []);

  useEffect(() => {
    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave]);

  return (
    <>
      {roomUrl && (
        <whereby-embed
          ref={wherebyRef}
          room={roomUrl}
          style={{ width: "100%", height: "98%" }}
        />
      )}
    </>
  );
}
