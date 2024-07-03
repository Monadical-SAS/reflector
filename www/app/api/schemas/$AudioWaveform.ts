export const $AudioWaveform = {
  properties: {
    data: {
      type: "array",
      contains: {
        type: "number",
      },
      isRequired: true,
    },
  },
} as const;
