import { VideoPlatform } from "../../api";
import { VideoPlatformAdapter } from "./types";
import { localConfig } from "../../../config-template";

// Platform implementations
import { WherebyAdapter } from "./whereby/WherebyAdapter";
import { JitsiAdapter } from "./jitsi/JitsiAdapter";

const platformAdapters: Record<VideoPlatform, VideoPlatformAdapter> = {
  whereby: WherebyAdapter,
  jitsi: JitsiAdapter,
};

export function getVideoPlatformAdapter(
  platform?: VideoPlatform,
): VideoPlatformAdapter {
  const selectedPlatform = platform || localConfig.video_platform;

  const adapter = platformAdapters[selectedPlatform];
  if (!adapter) {
    throw new Error(`Unsupported video platform: ${selectedPlatform}`);
  }

  return adapter;
}

export function getCurrentVideoPlatform(): VideoPlatform {
  return localConfig.video_platform;
}
