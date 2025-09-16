import { roomUrl } from "./routes";

export const roomAbsoluteUrl = (roomName: string) =>
  `${window.location.origin}${roomUrl(roomName)}`;
