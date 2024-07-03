export const $CreateParticipant = {
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
    name: {
      type: "string",
      isRequired: true,
    },
  },
} as const;
