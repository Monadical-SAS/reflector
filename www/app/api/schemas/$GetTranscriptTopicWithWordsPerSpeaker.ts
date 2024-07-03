export const $GetTranscriptTopicWithWordsPerSpeaker = {
  properties: {
    id: {
      type: "string",
      isRequired: true,
    },
    title: {
      type: "string",
      isRequired: true,
    },
    summary: {
      type: "string",
      isRequired: true,
    },
    timestamp: {
      type: "number",
      isRequired: true,
    },
    duration: {
      type: "any-of",
      contains: [
        {
          type: "number",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    transcript: {
      type: "string",
      isRequired: true,
    },
    segments: {
      type: "array",
      contains: {
        type: "GetTranscriptSegmentTopic",
      },
    },
    words_per_speaker: {
      type: "array",
      contains: {
        type: "SpeakerWords",
      },
    },
  },
} as const;
