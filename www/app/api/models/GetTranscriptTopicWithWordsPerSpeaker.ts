/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GetTranscriptSegmentTopic } from "./GetTranscriptSegmentTopic";
import type { SpeakerWords } from "./SpeakerWords";
export type GetTranscriptTopicWithWordsPerSpeaker = {
  id: string;
  title: string;
  summary: string;
  timestamp: number;
  duration: number | null;
  transcript: string;
  segments?: Array<GetTranscriptSegmentTopic>;
  words_per_speaker?: Array<SpeakerWords>;
};
