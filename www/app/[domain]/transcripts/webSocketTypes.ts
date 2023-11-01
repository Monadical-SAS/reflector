export type Topic = {
  timestamp: number;
  title: string;
  transcript: string;
  summary: string;
  id: string;
};

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
