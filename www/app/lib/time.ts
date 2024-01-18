// TODO format duraction in be ?

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
