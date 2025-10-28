"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { toaster } from "../../components/ui/toaster";
import { useRecordingConsent } from "../../recordingConsentContext";
import { useMeetingAudioConsent } from "../apiHooks";
import { ConsentDialog } from "./ConsentDialog";
import { TOAST_CHECK_INTERVAL_MS } from "./constants";
import type { ConsentDialogResult } from "./types";

export function useConsentDialog(meetingId: string): ConsentDialogResult {
  const { state: consentState, touch, hasConsent } = useRecordingConsent();
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

        touch(meetingId);
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

  return {
    showConsentModal,
    consentState,
    hasConsent,
    consentLoading: audioConsentMutation.isPending,
  };
}
