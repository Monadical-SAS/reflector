// Room name must be alphanumeric with hyphens and underscores only
const ROOM_NAME_REGEX = /^[a-zA-Z0-9_-]+$/;
const ROOM_NAME_MAX_LENGTH = 100;
const DISPLAY_NAME_MAX_LENGTH = 50;
const USER_ID_MAX_LENGTH = 50;

export function isValidRoomName(roomName: string): boolean {
  return (
    roomName.length > 0 &&
    roomName.length <= ROOM_NAME_MAX_LENGTH &&
    ROOM_NAME_REGEX.test(roomName)
  );
}

export function isValidDisplayName(displayName: string): boolean {
  return (
    displayName.length > 0 && displayName.length <= DISPLAY_NAME_MAX_LENGTH
  );
}

export function isValidUserId(userId: string): boolean {
  return userId.length > 0 && userId.length <= USER_ID_MAX_LENGTH;
}

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function getRoomNameError(roomName: string): string | null {
  if (roomName.length === 0) {
    return "Room name is required";
  }
  if (roomName.length > ROOM_NAME_MAX_LENGTH) {
    return `Room name must be ${ROOM_NAME_MAX_LENGTH} characters or less`;
  }
  if (!ROOM_NAME_REGEX.test(roomName)) {
    return "Room name can only contain letters, numbers, hyphens and underscores";
  }
  return null;
}
