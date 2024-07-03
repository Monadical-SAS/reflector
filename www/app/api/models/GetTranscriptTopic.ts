import type { GetTranscriptSegmentTopic } from "./GetTranscriptSegmentTopic";

export type GetTranscriptTopic = {
  id: string;
  title: string;
  summary: string;
  timestamp: number;
  duration: number | null;
  transcript: string;
  segments?: Array<GetTranscriptSegmentTopic>;
};
