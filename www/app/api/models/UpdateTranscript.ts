/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TranscriptParticipant } from "./TranscriptParticipant";
export type UpdateTranscript = {
  name?: string | null;
  locked?: boolean | null;
  title?: string | null;
  short_summary?: string | null;
  long_summary?: string | null;
  share_mode?: "public" | "semi-private" | "private" | null;
  participants?: Array<TranscriptParticipant> | null;
  reviewed?: boolean | null;
};
