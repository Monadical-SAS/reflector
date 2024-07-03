export const $CreateTranscript = {
  properties: {
    name: {
      type: "string",
      isRequired: true,
    },
    source_language: {
      type: "string",
    },
    target_language: {
      type: "string",
    },
  },
} as const;
