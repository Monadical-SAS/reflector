export const $RtcOffer = {
  properties: {
    sdp: {
      type: "string",
      isRequired: true,
    },
    type: {
      type: "string",
      isRequired: true,
    },
  },
} as const;
