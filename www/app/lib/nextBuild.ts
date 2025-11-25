import { isBuildPhase } from "./next";
import { assertExistsAndNonEmptyString, NonEmptyString } from "./utils";

const _getNextEnvVar = (name: string, e?: string): NonEmptyString =>
  isBuildPhase
    ? (() => {
        throw new Error(
          "panic! getNextEnvVar called during build phase; we don't support build envs",
        );
      })()
    : assertExistsAndNonEmptyString(
        process.env[name],
        `${name} is required; ${e}`,
      );

export const getNextEnvVar = (name: string, e?: string): NonEmptyString =>
  _getNextEnvVar(name, e);
