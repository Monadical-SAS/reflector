"use client";

import { Button, Icon } from "@chakra-ui/react";
import { FaBars } from "react-icons/fa6";
import { useConsentDialog } from "./useConsentDialog";
import {
  CONSENT_BUTTON_TOP_OFFSET,
  CONSENT_BUTTON_LEFT_OFFSET,
  CONSENT_BUTTON_Z_INDEX,
  CONSENT_DIALOG_TEXT,
} from "./constants";
import { MeetingId } from "../types";
import type { components } from "../../reflector-api";

type Meeting = components["schemas"]["Meeting"];

type ConsentDialogButtonProps = {
  meetingId: MeetingId;
  recordingType: Meeting["recording_type"];
  skipConsent: boolean;
};

export function ConsentDialogButton({
  meetingId,
  recordingType,
  skipConsent,
}: ConsentDialogButtonProps) {
  const { showConsentModal, consentState, showConsentButton, consentLoading } =
    useConsentDialog({ meetingId, recordingType, skipConsent });

  if (!consentState.ready || !showConsentButton || consentLoading) {
    return null;
  }

  return (
    <Button
      position="absolute"
      top={CONSENT_BUTTON_TOP_OFFSET}
      left={CONSENT_BUTTON_LEFT_OFFSET}
      zIndex={CONSENT_BUTTON_Z_INDEX}
      colorPalette="blue"
      size="sm"
      onClick={showConsentModal}
    >
      {CONSENT_DIALOG_TEXT.triggerButton}
      <Icon as={FaBars} ml={2} />
    </Button>
  );
}
