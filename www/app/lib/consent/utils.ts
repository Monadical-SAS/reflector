import type { components } from "../../reflector-api";

type Meeting = components["schemas"]["Meeting"];

/**
 * Determines if a meeting's recording type requires user consent.
 * Currently only "cloud" recordings require consent.
 */
export function recordingTypeRequiresConsent(
  recordingType: Meeting["recording_type"],
): boolean {
  return recordingType === "cloud";
}
