export interface JitsiUser {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
  moderator?: "true" | "false"; // JWT requires string "true"/"false"
}

export interface JitsiFeatures {
  recording?: boolean | string;
  livestreaming?: boolean | string;
  transcription?: boolean | string;
  "screen-sharing"?: boolean | string;
  "sip-inbound-call"?: boolean | string;
  "sip-outbound-call"?: boolean | string;
}

export interface JitsiJWTPayload {
  aud: "jitsi";
  iss: "chat";
  sub: string;
  exp: number;
  nbf: number;
  room: string;
  context: {
    user: JitsiUser;
    features?: JitsiFeatures;
  };
  iat?: number;
}

export interface JitsiConfigOverwrite {
  startWithAudioMuted?: boolean;
  startWithVideoMuted?: boolean;
  disableModeratorIndicator?: boolean;
  enableEmailInStats?: boolean;
  prejoinPageEnabled?: boolean;
  disableDeepLinking?: boolean;
  transcribingEnabled?: boolean;
  liveStreamingEnabled?: boolean;
  fileRecordingsEnabled?: boolean;
  requireDisplayName?: boolean;
}

export type JitsiToolbarButton =
  | "microphone"
  | "camera"
  | "desktop"
  | "fullscreen"
  | "recording"
  | "livestreaming"
  | "chat"
  | "settings"
  | "hangup"
  | "participants-pane"
  | "stats"
  | "tileview"
  | "filmstrip"
  | "invite"
  | "feedback"
  | "shortcuts"
  | "download"
  | "help"
  | "mute-everyone"
  | "e2ee";

export interface JitsiInterfaceConfigOverwrite {
  TOOLBAR_BUTTONS?: JitsiToolbarButton[];
  TOOLBAR_ALWAYS_VISIBLE?: boolean;
  SHOW_JITSI_WATERMARK?: boolean;
  SHOW_WATERMARK_FOR_GUESTS?: boolean;
  DEFAULT_BACKGROUND?: string;
  DISABLE_VIDEO_BACKGROUND?: boolean;
  MOBILE_APP_PROMO?: boolean;
  HIDE_INVITE_MORE_HEADER?: boolean;
}

export interface JitsiMeetOptions {
  roomName: string;
  jwt?: string;
  width?: string | number;
  height?: string | number;
  parentNode?: HTMLElement;
  configOverwrite?: JitsiConfigOverwrite;
  interfaceConfigOverwrite?: JitsiInterfaceConfigOverwrite;
  userInfo?: {
    displayName?: string;
    email?: string;
  };
  onload?: () => void;
}

export interface JitsiMeetExternalAPIConstructor {
  new (domain: string, options: JitsiMeetOptions): JitsiMeetExternalAPI;
}

export interface JitsiMeetExternalAPI {
  executeCommand(command: string, ...args: any[]): void;
  on(event: string, listener: (...args: any[]) => void): void;
  addListener(event: string, listener: (...args: any[]) => void): void;
  removeListener(event: string, listener: (...args: any[]) => void): void;
  dispose(): void;
  getVideoQuality(): number;
  isAudioMuted(): Promise<boolean>;
  isVideoMuted(): Promise<boolean>;
  getAudioQuality(): number;
  getCurrentDevices(): Promise<any>;
  getParticipantsInfo(): Promise<any>;
  getDisplayName(participantId: string): string;
  getEmail(participantId: string): string;
  getIFrame(): HTMLIFrameElement;
  isDeviceChangeAvailable(deviceType: string): Promise<boolean>;
  isDeviceListAvailable(): Promise<boolean>;
  isMultipleAudioInputSupported(): Promise<boolean>;
  pinParticipant(participantId: string): void;
  setAudioInputDevice(deviceLabel: string, deviceId: string): void;
  setAudioOutputDevice(deviceLabel: string, deviceId: string): void;
  setVideoInputDevice(deviceLabel: string, deviceId: string): void;
}

export interface JitsiParticipant {
  id: string;
  displayName: string;
  avatarUrl?: string;
  role?: "moderator" | "participant";
  isLocal?: boolean;
}

export interface JitsiRecordingStatus {
  on: boolean;
  mode?: "file" | "stream";
}

export interface JitsiParticipantEvent {
  id: string;
  displayName: string;
  avatarURL?: string;
  role?: string;
}

export interface JitsiVideoConferenceEvent {
  roomName: string;
  id: string;
  displayName: string;
}

export interface JitsiErrorEvent {
  message?: string;
  code?: string;
  details?: unknown;
}

export interface JitsiRecordingEvent {
  on: boolean;
  mode?: "file" | "stream";
  error?: string;
}

export type MeetingStateIdle = { type: "idle" };
export type MeetingStateGenerating = { type: "generating" };
export type MeetingStateLoading = { type: "loading" };
export type MeetingStateReady = {
  type: "ready";
  config: MeetingConfig;
  token: string;
};
export type MeetingStateJoined = {
  type: "joined";
  config: MeetingConfig;
  token: string;
};
export type MeetingStateError = {
  type: "error";
  error: Error;
};

export type MeetingState =
  | MeetingStateIdle
  | MeetingStateGenerating
  | MeetingStateLoading
  | MeetingStateReady
  | MeetingStateJoined
  | MeetingStateError;

export interface MeetingConfig {
  roomName: string;
  displayName: string;
  email?: string;
  isModerator: boolean;
  startWithAudioMuted: boolean;
  startWithVideoMuted: boolean;
  enableRecording: boolean;
  enableTranscription: boolean;
  enableLivestreaming: boolean;
}

export interface JaaSMeetingProps {
  appId: string;
  roomName: string;
  jwt?: string;
  configOverwrite?: JitsiConfigOverwrite;
  interfaceConfigOverwrite?: JitsiInterfaceConfigOverwrite;
  userInfo?: {
    displayName?: string;
    email?: string;
  };
  onApiReady?: (api: JitsiMeetExternalAPI) => void;
  onReadyToClose?: () => void;
  getIFrameRef?: (ref: HTMLIFrameElement) => void;
}

export interface JitsiApiReadyEvent {
  id: string;
  displayName?: string;
  avatarURL?: string;
  role?: string;
}

declare global {
  interface Window {
    JitsiMeetExternalAPI?: JitsiMeetExternalAPIConstructor;
  }
}
