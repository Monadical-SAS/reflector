"use client";

import { useCallback, useEffect, useRef, RefObject } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../reflector-api";
import { useAuth } from "../../lib/AuthProvider";
import { getWherebyUrl, useWhereby } from "../../lib/wherebyClient";
import { assertExistsAndNonEmptyString, NonEmptyString } from "../../lib/utils";
import {
  ConsentDialogButton as BaseConsentDialogButton,
  useConsentDialog,
  recordingTypeRequiresConsent,
} from "../../lib/consent";

type Meeting = components["schemas"]["Meeting"];

interface WherebyRoomProps {
  meeting: Meeting;
}

// Whereby-specific focus management for consent dialog
const useWherebyConsentFocusManagement = (
  wherebyRef: RefObject<HTMLElement>,
  shouldManageFocus: boolean,
) => {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!shouldManageFocus) return;

    const handleWherebyReady = () => {
      console.log("whereby ready - consent button should handle focus");
      previousFocusRef.current = document.activeElement as HTMLElement;
    };

    const element = wherebyRef.current;
    if (element) {
      element.addEventListener("ready", handleWherebyReady);
    } else {
      console.warn(
        "whereby ref not available for focus management - focus management disabled",
      );
    }

    return () => {
      element?.removeEventListener("ready", handleWherebyReady);
      previousFocusRef.current?.focus();
    };
  }, [wherebyRef, shouldManageFocus]);
};

function WherebyConsentDialogButton({
  meetingId,
  wherebyRef,
}: {
  meetingId: NonEmptyString;
  wherebyRef: React.RefObject<HTMLElement>;
}) {
  const { consentState, hasConsent, consentLoading } =
    useConsentDialog(meetingId);

  const shouldManageFocus =
    consentState.ready && !hasConsent(meetingId) && !consentLoading;

  useWherebyConsentFocusManagement(wherebyRef, shouldManageFocus);

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
        meetingId && (
          <WherebyConsentDialogButton
            meetingId={assertExistsAndNonEmptyString(meetingId)}
            wherebyRef={wherebyRef}
          />
        )}
    </>
  );
}
