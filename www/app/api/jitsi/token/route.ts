import { NextRequest, NextResponse } from "next/server";
import jwt from "jsonwebtoken";
import { JitsiJWTPayload } from "../../../(app)/jitsi-test/utils/types";
import {
  isValidRoomName,
  isValidDisplayName,
  isValidUserId,
  isValidEmail,
} from "../../../(app)/jitsi-test/utils/validation";

const APP_ID = process.env.JITSI_APP_ID;
if (!APP_ID) {
  throw new Error("JITSI_APP_ID environment variable is required");
}

const KEY_ID = process.env.JITSI_KEY_ID;
if (!KEY_ID) {
  throw new Error("JITSI_KEY_ID environment variable is required");
}

// The KID must match EXACTLY what was shown when you created the API key in Jitsi dashboard
const KID = `${APP_ID}/${KEY_ID}`;

interface TokenRequest {
  roomName: string;
  displayName: string;
  email?: string;
  userId: string;
  isModerator?: boolean;
  features?: {
    recording?: boolean;
    transcription?: boolean;
    livestreaming?: boolean;
  };
}

function getPrivateKey(): string {
  const privateKey = process.env.JITSI_PRIVATE_KEY;

  if (!privateKey) {
    throw new Error("JITSI_PRIVATE_KEY environment variable is not set");
  }

  // The key should already have proper newlines from .env.local
  // Just return it as-is
  return privateKey;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body: TokenRequest = await request.json();

    // Input validation
    if (!body.roomName || !body.displayName || !body.userId) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    // Use centralized validation utilities
    if (!isValidRoomName(body.roomName)) {
      return NextResponse.json(
        { error: "Invalid room name format" },
        { status: 400 },
      );
    }

    if (!isValidDisplayName(body.displayName)) {
      return NextResponse.json(
        { error: "Invalid display name" },
        { status: 400 },
      );
    }

    if (!isValidUserId(body.userId)) {
      return NextResponse.json({ error: "Invalid user ID" }, { status: 400 });
    }

    if (body.email && !isValidEmail(body.email)) {
      return NextResponse.json(
        { error: "Invalid email format" },
        { status: 400 },
      );
    }

    const now = Date.now();
    const nbf = Math.round((now - 10000) / 1000); // 10 seconds before now (in seconds)
    const iat = Math.round(now / 1000); // current time in seconds
    const exp = iat + 10800; // 3 hours from now (following official example)

    const payload: JitsiJWTPayload = {
      aud: "jitsi",
      iss: "chat",
      sub: APP_ID,
      exp,
      nbf,
      room: body.roomName, // Specific room access
      context: {
        user: {
          id: body.userId,
          name: body.displayName,
          email: body.email,
          moderator: body.isModerator ? "true" : "false",
        },
        features: {
          livestreaming: body.features?.livestreaming ? "true" : "false",
          recording: body.features?.recording ? "true" : "false",
          transcription: body.features?.transcription ? "true" : "false",
          "outbound-call": "false",
        },
      },
      iat,
    };

    const privateKey = getPrivateKey();

    // Log important values for debugging

    const token = jwt.sign(payload, privateKey, {
      algorithm: "RS256",
      header: {
        alg: "RS256",
        typ: "JWT",
        kid: KID,
      },
    });

    return NextResponse.json(
      { token },
      {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate",
          "X-Content-Type-Options": "nosniff",
        },
      },
    );
  } catch (error) {
    console.error("Failed to generate JWT:", error);
    return NextResponse.json(
      { error: "Failed to generate token" },
      { status: 500 },
    );
  }
}
