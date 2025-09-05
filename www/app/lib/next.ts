// next.js tries to run all the lib code during build phase; we don't always want it when e.g. we have connections initialized we don't want to have
export const isBuildPhase = process.env.NEXT_PHASE?.includes("build");
// for future usage - could be useful for "next build" conditional executions
export const isCI =
  process.env.CI === "true" ||
  process.env.IS_CI === "true" ||
  process.env.NEXT_PUBLIC_IS_CI === "true";
