module.exports = {
  testEnvironment: "jest-environment-jsdom",
  roots: ["<rootDir>/app"],
  testMatch: ["**/__tests__/**/*.test.ts", "**/__tests__/**/*.test.tsx"],
  collectCoverage: false,
  transform: {
    "^.+\\.[jt]sx?$": [
      "ts-jest",
      {
        tsconfig: {
          jsx: "react-jsx",
          module: "esnext",
          moduleResolution: "bundler",
          esModuleInterop: true,
          strict: false,
          strictNullChecks: true,
          downlevelIteration: true,
          lib: ["dom", "dom.iterable", "esnext"],
        },
      },
    ],
  },
};
