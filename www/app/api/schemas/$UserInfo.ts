export const $UserInfo = {
  properties: {
    sub: {
      type: "string",
      isRequired: true,
    },
    email: {
      type: "any-of",
      contains: [
        {
          type: "string",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
    email_verified: {
      type: "any-of",
      contains: [
        {
          type: "boolean",
        },
        {
          type: "null",
        },
      ],
      isRequired: true,
    },
  },
} as const;
