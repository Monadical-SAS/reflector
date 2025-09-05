import type { components } from "../../reflector-api";

type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];

export type Topic = GetTranscriptTopic;

export type Transcript = {
  text: string;
};

export type FinalSummary = {
  summary: string;
};

export type Status = {
  value: string;
};

export type TranslatedTopic = {
  text: string;
  translation: string;
};
