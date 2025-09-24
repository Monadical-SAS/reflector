import { JitsiJWTPayload, JitsiUser, JitsiFeatures } from "./types";

// APP_ID should come from environment variables, not hardcoded

export interface GenerateJWTOptions {
  roomName: string;
  user: JitsiUser;
  features?: JitsiFeatures;
  expirationHours?: number;
}

export async function generateJitsiJWT({
  roomName,
  user,
  features = {
    recording: true,
    transcription: true,
    livestreaming: false,
  },
  expirationHours = 2,
}: GenerateJWTOptions): Promise<string> {
  const response = await fetch("/api/jitsi/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      roomName,
      displayName: user.name,
      email: user.email,
      userId: user.id,
      isModerator: user.moderator === "true",
      features,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to generate JWT token");
  }

  const data = await response.json();
  return data.token;
}

export function decodeJWT(token: string): JitsiJWTPayload | null {
  try {
    // Simple base64 decode for client-side (not verifying signature)
    const parts = token.split(".");
    if (parts.length !== 3) {
      console.warn("Invalid JWT format: expected 3 parts");
      return null;
    }

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded) as JitsiJWTPayload;
  } catch (error) {
    console.error("Failed to decode JWT:", error);
    return null;
  }
}

export function generateRoomName(prefix: string = "test"): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}-${timestamp}-${random}`;
}
