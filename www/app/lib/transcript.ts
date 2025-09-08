import { components } from "../reflector-api";
import { Equals } from "./types";

type ApiTranscriptStatus = components["schemas"]["GetTranscript"]["status"];

export const TRANSCRIPT_STATUSES = [
  "idle",
  "uploaded",
  "recording",
  "processing",
  "error",
  "ended",
] as const;

export type TranscriptStatus = (typeof TRANSCRIPT_STATUSES)[number];

// noinspection JSUnusedLocalSymbols
const _assert: Equals<ApiTranscriptStatus, TranscriptStatus> = true;
