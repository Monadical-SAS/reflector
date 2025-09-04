import { VideoPlatform } from "../../api";

export const getPlatformDisplayName = (platform?: VideoPlatform): string => {
  switch (platform) {
    case "whereby":
      return "Whereby";
    case "jitsi":
      return "Jitsi Meet";
    default:
      return "Whereby"; // Default fallback
  }
};

export const getPlatformColor = (platform?: VideoPlatform): string => {
  switch (platform) {
    case "whereby":
      return "blue";
    case "jitsi":
      return "green";
    default:
      return "blue"; // Default fallback
  }
};
