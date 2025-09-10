/**
 * @jest-environment node
 */

import { getFeatureEnvVarName } from "../config";

describe("getFeatureEnvVarName", () => {
  test("converts camelCase to SCREAMING_SNAKE_CASE with prefix", () => {
    expect(getFeatureEnvVarName("requireLogin")).toBe(
      "NEXT_PUBLIC_FEATURE_REQUIRE_LOGIN",
    );
    expect(getFeatureEnvVarName("sendToZulip")).toBe(
      "NEXT_PUBLIC_FEATURE_SEND_TO_ZULIP",
    );
    expect(getFeatureEnvVarName("privacy")).toBe("NEXT_PUBLIC_FEATURE_PRIVACY");
    expect(getFeatureEnvVarName("browse")).toBe("NEXT_PUBLIC_FEATURE_BROWSE");
    expect(getFeatureEnvVarName("rooms")).toBe("NEXT_PUBLIC_FEATURE_ROOMS");
  });
  test("handles multiple capital letters", () => {
    expect(getFeatureEnvVarName("sendToZulip")).toBe(
      "NEXT_PUBLIC_FEATURE_SEND_TO_ZULIP",
    );
  });
});
