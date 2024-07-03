import type { GetTranscriptSegmentTopic } from "./GetTranscriptSegmentTopic";
import type { Word } from "./Word";

export type GetTranscriptTopicWithWords = {
  id: string;
  title: string;
  summary: string;
  timestamp: number;
  duration: number | null;
  transcript: string;
  segments?: Array<GetTranscriptSegmentTopic>;
  words?: Array<Word>;
};
