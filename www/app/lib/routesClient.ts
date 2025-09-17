import { roomUrl } from "./routes";
import { NonEmptyString } from "./utils";

export const roomAbsoluteUrl = (roomName: NonEmptyString) =>
  `${window.location.origin}${roomUrl(roomName)}`;
