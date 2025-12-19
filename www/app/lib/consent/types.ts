export interface ConsentDialogResult {
  showConsentModal: () => void;
  consentState: {
    ready: boolean;
    consentForMeetings?: Map<string, boolean>;
  };
  hasAnswered: (meetingId: string) => boolean;
  hasAccepted: (meetingId: string) => boolean;
  consentLoading: boolean;
}
