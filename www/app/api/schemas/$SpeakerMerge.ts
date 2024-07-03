export const $SpeakerMerge = {
  properties: {
    speaker_from: {
      type: "number",
      isRequired: true,
    },
    speaker_to: {
      type: "number",
      isRequired: true,
    },
  },
} as const;
