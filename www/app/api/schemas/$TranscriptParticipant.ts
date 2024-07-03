export const $TranscriptParticipant = {
  properties: {
    id: {
      type: "string",
    },
    speaker: {
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
    name: {
      type: "string",
      isRequired: true,
    },
  },
} as const;
