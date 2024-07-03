/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TranscriptParticipant } from "./TranscriptParticipant";
export type GetTranscript = {
  id: string;
  user_id: string | null;
  name: string;
  status: string;
  locked: boolean;
  duration: number;
  title: string | null;
  short_summary: string | null;
  long_summary: string | null;
  created_at: string;
  share_mode?: string;
  source_language: string | null;
  target_language: string | null;
  participants: Array<TranscriptParticipant> | null;
  reviewed: boolean;
};
