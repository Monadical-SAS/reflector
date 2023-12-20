export type ShareMode = "public" | "semi-private" | "private" | null;

export function toShareMode(value: string | undefined | null): ShareMode {
  return value === "public" || value === "semi-private" || value === "private"
    ? value
    : null;
}
