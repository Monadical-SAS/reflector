export const $GetTranscriptSegmentTopic = {
  properties: {
    text: {
      type: "string",
      isRequired: true,
    },
    start: {
      type: "number",
      isRequired: true,
    },
    speaker: {
      type: "number",
      isRequired: true,
    },
  },
} as const;
