// next.js tries to run all the lib code during build phase; we don't always want it when e.g. we have connections initialized we don't want to have
export const isBuildPhase = process.env.NEXT_PHASE?.includes("build");
