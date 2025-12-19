import { MeetingId } from "../types";

export type ConsentDialogResult = {
  showConsentModal: () => void;
  consentState: {
    ready: boolean;
    consentForMeetings?: Map<MeetingId, boolean>;
  };
  hasAnswered: (meetingId: MeetingId) => boolean;
  hasAccepted: (meetingId: MeetingId) => boolean;
  consentLoading: boolean;
  showRecordingIndicator: boolean;
  showConsentButton: boolean;
};
