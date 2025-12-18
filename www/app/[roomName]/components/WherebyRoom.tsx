"use client";

import { useCallback, useEffect, useRef, RefObject } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import { getWherebyUrl, useWhereby } from "../../lib/wherebyClient";
import { assertExistsAndNonEmptyString, NonEmptyString } from "../../lib/utils";
import {
  ConsentDialogButton as BaseConsentDialogButton,
  RecordingIndicator,
  useConsentDialog,
  recordingTypeRequiresConsent,
} from "../../lib/consent";

type Meeting = components["schemas"]["Meeting"];

interface WherebyRoomProps {
  meeting: Meeting;
}

function WherebyConsentDialogButton({
  meetingId,
  wherebyRef,
}: {
  meetingId: NonEmptyString;
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

  return <BaseConsentDialogButton meetingId={meetingId} />;
}

export default function WherebyRoom({ meeting }: WherebyRoomProps) {
  const wherebyLoaded = useWhereby();
  const wherebyRef = useRef<HTMLElement>(null);
  const router = useRouter();
  const auth = useAuth();
  const status = auth.status;
  const isAuthenticated = status === "authenticated";

  const wherebyRoomUrl = getWherebyUrl(meeting);
  const recordingType = meeting.recording_type;
  const meetingId = meeting.id;

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
      {recordingType &&
        recordingTypeRequiresConsent(recordingType) &&
        meetingId &&
        (meeting.skip_consent ? (
          <RecordingIndicator />
        ) : (
          <WherebyConsentDialogButton
            meetingId={assertExistsAndNonEmptyString(meetingId)}
            wherebyRef={wherebyRef}
          />
        ))}
    </>
  );
}
