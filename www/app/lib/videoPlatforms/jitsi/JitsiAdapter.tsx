import { VideoPlatformAdapter } from "../types";
import JitsiProvider from "./JitsiProvider";

export const JitsiAdapter: VideoPlatformAdapter = {
  component: JitsiProvider,
  requiresConsent: true,
  supportsFocusManagement: false, // Jitsi iframe doesn't support the same focus management as Whereby
};
