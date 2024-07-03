export const $UpdateTranscript = {
  properties: {
    name: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
    },
    locked: {
      type: "any-of",
      contains: [
        {
          type: "boolean",
        },
        {
          type: "null",
        },
      ],
    },
    title: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
    },
    short_summary: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
    },
    long_summary: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
    },
    share_mode: {
      type: "any-of",
      contains: [
        {
          type: "Enum",
        },
        {
          type: "null",
        },
      ],
    },
    participants: {
      type: "any-of",
      contains: [
        {
          type: "array",
          contains: {
            type: "TranscriptParticipant",
          },
        },
        {
          type: "null",
        },
      ],
    },
    reviewed: {
      type: "any-of",
      contains: [
        {
          type: "boolean",
        },
        {
          type: "null",
        },
      ],
    },
  },
} as const;
