import {
  JitsiConfigOverwrite,
  JitsiInterfaceConfigOverwrite,
  JitsiToolbarButton,
} from "./types";

import { getClientEnv } from "../../../lib/clientEnv";

export const JITSI_DOMAIN = "8x8.vc";

export function getAppId(): string {
  const env = getClientEnv();
  if (!env.JITSI_APP_ID) {
    throw new Error("JITSI_APP_ID not configured");
  }
  return env.JITSI_APP_ID;
}

export function getFullRoomName(roomName: string): string {
  return `${getAppId()}/${roomName}`;
}

export const DEFAULT_TOOLBAR_BUTTONS: JitsiToolbarButton[] = [
  "microphone",
  "camera",
  "desktop",
  "fullscreen",
  "recording",
  "chat",
  "settings",
  "hangup",
  "participants-pane",
  "stats",
  "tileview",
  "filmstrip",
];

export const DEFAULT_CONFIG_OVERWRITE: JitsiConfigOverwrite = {
  startWithAudioMuted: true,
  startWithVideoMuted: true,
  disableModeratorIndicator: false,
  enableEmailInStats: true,
  prejoinPageEnabled: false,
  disableDeepLinking: true,
  transcribingEnabled: false,
  liveStreamingEnabled: false,
  fileRecordingsEnabled: true,
  requireDisplayName: false,
};

export const DEFAULT_INTERFACE_CONFIG_OVERWRITE: JitsiInterfaceConfigOverwrite =
  {
    TOOLBAR_BUTTONS: DEFAULT_TOOLBAR_BUTTONS,
    TOOLBAR_ALWAYS_VISIBLE: false,
    SHOW_JITSI_WATERMARK: false,
    SHOW_WATERMARK_FOR_GUESTS: false,
    DISABLE_VIDEO_BACKGROUND: false,
    MOBILE_APP_PROMO: false,
    HIDE_INVITE_MORE_HEADER: true,
  };

export function loadJitsiScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (typeof window !== "undefined" && window.JitsiMeetExternalAPI) {
      resolve();
      return;
    }

    // Check if script already exists in DOM
    const existingScript = document.querySelector(
      `script[src="https://${JITSI_DOMAIN}/external_api.js"]`,
    );
    if (existingScript) {
      // Wait a bit for it to load
      const checkInterval = setInterval(() => {
        if (window.JitsiMeetExternalAPI) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);

      // Timeout after 10 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        reject(new Error("Timeout waiting for Jitsi API to load"));
      }, 10000);
      return;
    }

    const script = document.createElement("script");
    script.src = `https://${JITSI_DOMAIN}/external_api.js`;
    script.async = true;
    script.onload = () => {
      resolve();
    };
    script.onerror = (error) => {
      console.error("Failed to load Jitsi script:", error);
      reject(new Error("Failed to load Jitsi Meet External API"));
    };
    document.body.appendChild(script);
  });
}
