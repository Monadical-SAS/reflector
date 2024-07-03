export const $Word = {
  properties: {
    text: {
      type: "string",
      isRequired: true,
    },
    start: {
      type: "number",
      isRequired: true,
    },
    end: {
      type: "number",
      isRequired: true,
    },
    speaker: {
      type: "number",
    },
  },
} as const;
