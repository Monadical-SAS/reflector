export const formatDateTime = (d: Date): string => {
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatStartedAgo = (
  startTime: Date,
  now: Date = new Date(),
): string => {
  const diff = now.getTime() - startTime.getTime();

  if (diff <= 0) return "Starting now";

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `Started ${days}d ${hours % 24}h ${minutes % 60}m ago`;
  if (hours > 0) return `Started ${hours}h ${minutes % 60}m ago`;
  return `Started ${minutes} minutes ago`;
};
