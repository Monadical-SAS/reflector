export const $SpeakerAssignment = {
  properties: {
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
    },
    participant: {
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
    timestamp_from: {
      type: "number",
      isRequired: true,
    },
    timestamp_to: {
      type: "number",
      isRequired: true,
    },
  },
} as const;
