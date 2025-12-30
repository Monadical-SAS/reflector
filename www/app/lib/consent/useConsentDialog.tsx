"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { toaster } from "../../components/ui/toaster";
import { useRecordingConsent } from "../../recordingConsentContext";
import { useMeetingAudioConsent } from "../apiHooks";
import { ConsentDialog } from "./ConsentDialog";
import { TOAST_CHECK_INTERVAL_MS } from "./constants";
import type { ConsentDialogResult } from "./types";
import { MeetingId } from "../types";
import { recordingTypeRequiresConsent } from "./utils";
import type { components } from "../../reflector-api";

type Meeting = components["schemas"]["Meeting"];

type UseConsentDialogParams = {
  meetingId: MeetingId;
  recordingType: Meeting["recording_type"];
  skipConsent: boolean;
};

export function useConsentDialog({
  meetingId,
  recordingType,
  skipConsent,
}: UseConsentDialogParams): ConsentDialogResult {
  const {
    state: consentState,
    touch,
    hasAnswered,
    hasAccepted,
  } = useRecordingConsent();
  const [modalOpen, setModalOpen] = useState(false);
  const audioConsentMutation = useMeetingAudioConsent();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const keydownHandlerRef = useRef<((event: KeyboardEvent) => void) | null>(
    null,
  );

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (keydownHandlerRef.current) {
        document.removeEventListener("keydown", keydownHandlerRef.current);
        keydownHandlerRef.current = null;
      }
    };
  }, []);

  const handleConsent = useCallback(
    async (given: boolean) => {
      try {
        await audioConsentMutation.mutateAsync({
          params: {
            path: { meeting_id: meetingId },
          },
          body: {
            consent_given: given,
          },
        });

        touch(meetingId, given);
      } catch (error) {
        console.error("Error submitting consent:", error);
      }
    },
    [audioConsentMutation, touch, meetingId],
  );

  const showConsentModal = useCallback(() => {
    if (modalOpen) return;

    setModalOpen(true);

    const toastId = toaster.create({
      placement: "top",
      duration: null,
      render: ({ dismiss }) => (
        <ConsentDialog
          onAccept={() => {
            handleConsent(true);
            dismiss();
          }}
          onReject={() => {
            handleConsent(false);
            dismiss();
          }}
        />
      ),
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        toastId.then((id) => toaster.dismiss(id));
      }
    };

    keydownHandlerRef.current = handleKeyDown;
    document.addEventListener("keydown", handleKeyDown);

    toastId.then((id) => {
      intervalRef.current = setInterval(() => {
        if (!toaster.isActive(id)) {
          setModalOpen(false);

          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }

          if (keydownHandlerRef.current) {
            document.removeEventListener("keydown", keydownHandlerRef.current);
            keydownHandlerRef.current = null;
          }
        }
      }, TOAST_CHECK_INTERVAL_MS);
    });
  }, [handleConsent, modalOpen]);

  const requiresConsent = Boolean(
    recordingType && recordingTypeRequiresConsent(recordingType),
  );

  const showRecordingIndicator =
    requiresConsent && (skipConsent || hasAccepted(meetingId));

  const showConsentButton =
    requiresConsent && !skipConsent && !hasAnswered(meetingId);

  return {
    showConsentModal,
    consentState,
    hasAnswered,
    hasAccepted,
    consentLoading: audioConsentMutation.isPending,
    showRecordingIndicator,
    showConsentButton,
  };
}
