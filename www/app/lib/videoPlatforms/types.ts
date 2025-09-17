import { RefObject, ReactNode } from "react";
import { VideoPlatform, Meeting } from "../../api";

export interface VideoPlatformProviderProps {
  meeting: Meeting;
  onConsentGiven?: () => void;
  onConsentDeclined?: () => void;
  children?: ReactNode;
}

export interface VideoPlatformContextValue {
  platform: VideoPlatform;
  meeting: Meeting | null;
  isReady: boolean;
  hasConsent: boolean;
  giveConsent: () => void;
  declineConsent: () => void;
}

export interface VideoPlatformComponentProps {
  meeting: Meeting;
  roomRef?: RefObject<HTMLElement>;
  onReady?: () => void;
  onConsentGiven?: () => void;
  onConsentDeclined?: () => void;
}

export interface VideoPlatformAdapter {
  component: React.ComponentType<VideoPlatformComponentProps>;
  requiresConsent: boolean;
  supportsFocusManagement: boolean;
}
