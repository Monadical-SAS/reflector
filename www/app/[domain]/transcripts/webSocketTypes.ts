export type SegmentTopic = {
  speaker: number;
  start: number;
  text: string;
};

export type Topic = {
  timestamp: number;
  title: string;
  summary: string;
  id: string;
  text: string;
  segments: SegmentTopic[];
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
