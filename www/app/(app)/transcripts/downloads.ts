import type { components } from "../../reflector-api";

export type DownloadEntry = components["schemas"]["DownloadEntry"];

export type ParticipantDownloads = {
  name: string;
  entries: DownloadEntry[];
};

export type GroupedDownloads = {
  transcript: DownloadEntry[];
  recording: DownloadEntry[];
  participants: ParticipantDownloads[];
};

const TRANSCRIPT_KINDS = new Set<DownloadEntry["kind"]>([
  "text",
  "subtitles",
  "summary",
]);
const RECORDING_KINDS = new Set<DownloadEntry["kind"]>([
  "audio",
  "cloud_video",
]);
const UNKNOWN_PARTICIPANT = "Unknown participant";
const UNITS = ["B", "KB", "MB", "GB", "TB"];

export function formatSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "";
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rounded =
    value >= 10 || unit === 0 ? Math.round(value) : value.toFixed(1);
  return `${rounded} ${UNITS[unit]}`;
}

export function groupDownloads(entries: DownloadEntry[]): GroupedDownloads {
  const participants = new Map<string, DownloadEntry[]>();
  for (const entry of entries) {
    if (entry.kind !== "track") continue;
    const name = entry.participant_name ?? UNKNOWN_PARTICIPANT;
    participants.set(name, [...(participants.get(name) ?? []), entry]);
  }
  return {
    transcript: entries.filter((e) => TRANSCRIPT_KINDS.has(e.kind)),
    recording: entries.filter((e) => RECORDING_KINDS.has(e.kind)),
    participants: [...participants].map(([name, items]) => ({
      name,
      entries: items,
    })),
  };
}

export function resolveDownloadUrl(url: string, apiUrl: string): string {
  return url.startsWith("/") ? `${apiUrl}${url}` : url;
}

export function buildZipUrl(
  zipUrl: string,
  ids: string[],
  apiUrl: string,
): string {
  const params = ids.map((id) => `&ids=${encodeURIComponent(id)}`).join("");
  return resolveDownloadUrl(zipUrl, apiUrl) + params;
}

export function startDownload(url: string, filename?: string) {
  const a = document.createElement("a");
  a.href = url;
  if (filename) a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}
