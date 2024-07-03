export const $Page_GetTranscript_ = {
  properties: {
    items: {
      type: "array",
      contains: {
        type: "GetTranscript",
      },
      isRequired: true,
    },
    total: {
      type: "number",
      isRequired: true,
    },
    page: {
      type: "any-of",
      contains: [
        {
          type: "number",
          minimum: 1,
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    size: {
      type: "any-of",
      contains: [
        {
          type: "number",
          minimum: 1,
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    pages: {
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
  },
} as const;
