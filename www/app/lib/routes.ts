import { NonEmptyString } from "./utils";

export const roomUrl = (roomName: NonEmptyString) => `/${roomName}`;
export const roomMeetingUrl = (
  roomName: NonEmptyString,
  meetingId: NonEmptyString,
) => `${roomUrl(roomName)}/${meetingId}`;
