export const $Participant = {
  properties: {
    id: {
      type: "string",
      isRequired: true,
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
