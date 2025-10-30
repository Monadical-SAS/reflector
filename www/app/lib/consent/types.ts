export interface ConsentDialogResult {
  showConsentModal: () => void;
  consentState: {
    ready: boolean;
    consentAnsweredForMeetings?: Set<string>;
  };
  hasConsent: (meetingId: string) => boolean;
  consentLoading: boolean;
}
