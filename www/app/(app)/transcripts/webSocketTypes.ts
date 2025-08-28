import { GetTranscriptTopic } from "../../lib/api-types";

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
