export const formatTimeMs = (milliseconds: number): string => {
  return formatTime(Math.floor(milliseconds / 1000));
};

export const formatTime = (seconds: number): string => {
  let hours = Math.floor(seconds / 3600);
  let minutes = Math.floor((seconds % 3600) / 60);
  let secs = Math.floor(seconds % 60);

  let timeString = `${hours > 0 ? hours + ":" : ""}${minutes
    .toString()
    .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;

  return timeString;
};

export const formatTimeDifference = (seconds: number): string => {
  let hours = Math.floor(seconds / 3600);
  let minutes = Math.floor((seconds % 3600) / 60);
  let secs = Math.floor(seconds % 60);

  let timeString =
    hours > 0
      ? `${hours < 10 ? "\u00A0" : ""}${hours}h ago`
      : minutes > 0
      ? `${minutes < 10 ? "\u00A0" : ""}${minutes}m ago`
      : `<1m ago`;

  return timeString;
};

export const formatRelativeTime = (dateString: string): string => {
  const now = new Date();
  const past = new Date(dateString);
  const diffMs = now.getTime() - past.getTime();

  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

export const formatLocalDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString(navigator.language || "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
  });
};
