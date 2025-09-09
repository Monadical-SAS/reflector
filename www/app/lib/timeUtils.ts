export const formatDateTime = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatCountdown = (startTime: string | Date): string => {
  const now = new Date();
  const start = new Date(startTime);
  const diff = start.getTime() - now.getTime();

  if (diff <= 0) return "Starting now";

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `Starts in ${days}d ${hours % 24}h ${minutes % 60}m`;
  if (hours > 0) return `Starts in ${hours}h ${minutes % 60}m`;
  return `Starts in ${minutes} minutes`;
};

export const formatStartedAgo = (startTime: string | Date): string => {
  const now = new Date();
  const start = new Date(startTime);
  const diff = now.getTime() - start.getTime();

  if (diff <= 0) return "Starting now";

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `Started ${days}d ${hours % 24}h ${minutes % 60}m ago`;
  if (hours > 0) return `Started ${hours}h ${minutes % 60}m ago`;
  return `Started ${minutes} minutes ago`;
};
