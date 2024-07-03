export const $GetTranscript = {
  properties: {
    id: {
      type: "string",
      isRequired: true,
    },
    user_id: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    name: {
      type: "string",
      isRequired: true,
    },
    status: {
      type: "string",
      isRequired: true,
    },
    locked: {
      type: "boolean",
      isRequired: true,
    },
    duration: {
      type: "number",
      isRequired: true,
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
      isRequired: true,
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
      isRequired: true,
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
      isRequired: true,
    },
    created_at: {
      type: "string",
      isRequired: true,
      format: "date-time",
    },
    share_mode: {
      type: "string",
    },
    source_language: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    target_language: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
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
      isRequired: true,
    },
    reviewed: {
      type: "boolean",
      isRequired: true,
    },
  },
} as const;
