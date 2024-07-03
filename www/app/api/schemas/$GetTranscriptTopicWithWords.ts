export const $GetTranscriptTopicWithWords = {
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
    words: {
      type: "array",
      contains: {
        type: "Word",
      },
    },
  },
} as const;
