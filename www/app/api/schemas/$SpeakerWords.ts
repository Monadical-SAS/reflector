export const $SpeakerWords = {
  properties: {
    speaker: {
      type: "number",
      isRequired: true,
    },
    words: {
      type: "array",
      contains: {
        type: "Word",
      },
      isRequired: true,
    },
  },
} as const;
