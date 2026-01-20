// Predefined color palette for topics
// Colors chosen for good contrast and visual distinction
export const TOPIC_COLORS = [
  "#3B82F6", // blue
  "#10B981", // green
  "#F59E0B", // amber
  "#EF4444", // red
  "#8B5CF6", // violet
  "#EC4899", // pink
  "#14B8A6", // teal
  "#F97316", // orange
  "#6366F1", // indigo
  "#84CC16", // lime
] as const;

export function getTopicColor(topicIndex: number): string {
  return TOPIC_COLORS[topicIndex % TOPIC_COLORS.length];
}
