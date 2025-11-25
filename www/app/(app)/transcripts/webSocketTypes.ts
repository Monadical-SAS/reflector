import type { components } from "../../reflector-api";
import type { TranscriptStatus } from "../../lib/transcript";

type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];

export type Topic = GetTranscriptTopic;

export type Transcript = {
  text: string;
};

export type FinalSummary = {
  summary: string;
};

export type Status = {
  value: TranscriptStatus;
};

export type TranslatedTopic = {
  text: string;
  translation: string;
};
