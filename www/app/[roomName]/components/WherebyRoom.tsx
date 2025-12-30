"use client";

import { useCallback, useEffect, useRef, RefObject } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import { getWherebyUrl, useWhereby } from "../../lib/wherebyClient";
import {
  ConsentDialogButton as BaseConsentDialogButton,
  useConsentDialog,
} from "../../lib/consent";
import { assertMeetingId, MeetingId } from "../../lib/types";

type Meeting = components["schemas"]["Meeting"];
type Room = components["schemas"]["RoomDetails"];

interface WherebyRoomProps {
  meeting: Meeting;
  room: Room;
}

function WherebyConsentDialogButton({
  meetingId,
  recordingType,
  skipConsent,
  wherebyRef,
}: {
  meetingId: MeetingId;
  recordingType: Meeting["recording_type"];
  skipConsent: boolean;
  wherebyRef: React.RefObject<HTMLElement>;
}) {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = wherebyRef.current;
    if (!element) return;

    const handleWherebyReady = () => {
      previousFocusRef.current = document.activeElement as HTMLElement;
    };

    element.addEventListener("ready", handleWherebyReady);

    return () => {
      element.removeEventListener("ready", handleWherebyReady);
      if (previousFocusRef.current && document.activeElement === element) {
        previousFocusRef.current.focus();
      }
    };
  }, [wherebyRef]);

  return (
    <BaseConsentDialogButton
      meetingId={meetingId}
      recordingType={recordingType}
      skipConsent={skipConsent}
    />
  );
}

export default function WherebyRoom({ meeting, room }: WherebyRoomProps) {
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";

  const wherebyRoomUrl = getWherebyUrl(meeting);
  const meetingId = meeting.id;

  const { showConsentButton } = useConsentDialog({
    meetingId: assertMeetingId(meetingId),
    recordingType: meeting.recording_type,
    skipConsent: room.skip_consent,
  });

  const isLoading = status === "loading";

  const handleLeave = useCallback(() => {
    router.push("/browse");
  }, [router]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !wherebyRoomUrl || !wherebyLoaded)
      return;

    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave, wherebyRoomUrl, isLoading, isAuthenticated, wherebyLoaded]);

  if (!wherebyRoomUrl || !wherebyLoaded) {
    return null;
  }

  return (
    <>
      <whereby-embed
        ref={wherebyRef}
        room={wherebyRoomUrl}
        style={{ width: "100vw", height: "100vh" }}
      />
      {showConsentButton && (
        <WherebyConsentDialogButton
          meetingId={assertMeetingId(meetingId)}
          recordingType={meeting.recording_type}
          skipConsent={room.skip_consent}
          wherebyRef={wherebyRef}
        />
      )}
    </>
  );
}
