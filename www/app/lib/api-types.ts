// Re-export types from generated OpenAPI schema for backward compatibility
import type { components } from "../reflector-api";

// Export types with their original names
export type Room = components["schemas"]["Room"];
export type Meeting = components["schemas"]["Meeting"];
export type SourceKind = components["schemas"]["SourceKind"];
export type SearchResult = components["schemas"]["SearchResult"];
export type GetTranscript = components["schemas"]["GetTranscript"];
export type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
export type UpdateTranscript = components["schemas"]["UpdateTranscript"];
export type AudioWaveform = components["schemas"]["AudioWaveform"];
export type Participant = components["schemas"]["Participant"];
export type CreateTranscript = components["schemas"]["CreateTranscript"];
export type RtcOffer = components["schemas"]["RtcOffer"];
export type GetTranscriptSegmentTopic =
  components["schemas"]["GetTranscriptSegmentTopic"];
export type Page_Room_ = components["schemas"]["Page_Room_"];
export type ApiError = components["schemas"]["ApiError"];
export type GetTranscriptTopicWithWordsPerSpeaker =
  components["schemas"]["GetTranscriptTopicWithWordsPerSpeaker"];
export type GetTranscriptMinimal =
  components["schemas"]["GetTranscriptMinimal"];

// Export any enums or constants that were in the old API
export const $SourceKind = {
  values: ["SINGLE", "CALL", "WHEREBY", "UPLOAD"] as const,
} as const;
