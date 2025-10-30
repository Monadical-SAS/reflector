export const CONSENT_BUTTON_TOP_OFFSET = "56px";
export const CONSENT_BUTTON_LEFT_OFFSET = "8px";
export const CONSENT_BUTTON_Z_INDEX = 1000;
export const TOAST_CHECK_INTERVAL_MS = 100;

export const CONSENT_DIALOG_TEXT = {
  question:
    "Can we have your permission to store this meeting's audio recording on our servers?",
  acceptButton: "Yes, store the audio",
  rejectButton: "No, delete after transcription",
  triggerButton: "Meeting is being recorded",
} as const;
