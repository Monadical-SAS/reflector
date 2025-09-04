import { VideoPlatformAdapter } from "../types";
import WherebyProvider from "./WherebyProvider";

export const WherebyAdapter: VideoPlatformAdapter = {
  component: WherebyProvider,
  requiresConsent: true,
  supportsFocusManagement: true,
};
