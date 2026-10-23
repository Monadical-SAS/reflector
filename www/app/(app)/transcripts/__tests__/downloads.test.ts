import {
  buildZipUrl,
  formatSize,
  groupDownloads,
  resolveDownloadUrl,
  type DownloadEntry,
} from "../downloads";

const entry = (
  id: string,
  kind: DownloadEntry["kind"],
  participant_name: string | null = null,
): DownloadEntry => ({
  id,
  kind,
  label: id,
  participant_name,
  filename: `${id}.bin`,
  size: null,
  url: `/v1/transcripts/t1/download/file/${id}?token=abc`,
});

describe("formatSize", () => {
  it("formats bytes with one unit", () => {
    expect(formatSize(512)).toBe("512 B");
    expect(formatSize(12 * 1024)).toBe("12 KB");
    expect(formatSize(44 * 1024 * 1024)).toBe("44 MB");
    expect(formatSize(1.5 * 1024 * 1024 * 1024)).toBe("1.5 GB");
  });

  it("returns an empty string when the size is unknown", () => {
    expect(formatSize(null)).toBe("");
    expect(formatSize(undefined)).toBe("");
  });
});

describe("groupDownloads", () => {
  it("splits entries into sections and groups tracks by participant", () => {
    const groups = groupDownloads([
      entry("text", "text"),
      entry("summary", "summary"),
      entry("audio", "audio"),
      entry("cloud_video", "cloud_video"),
      entry("a1", "track", "Alice"),
      entry("a2", "track", "Alice"),
      entry("b1", "track", "Bob"),
      entry("x1", "track", null),
    ]);

    expect(groups.transcript.map((e) => e.id)).toEqual(["text", "summary"]);
    expect(groups.recording.map((e) => e.id)).toEqual(["audio", "cloud_video"]);
    expect(
      groups.participants.map((p) => [p.name, p.entries.map((e) => e.id)]),
    ).toEqual([
      ["Alice", ["a1", "a2"]],
      ["Bob", ["b1"]],
      ["Unknown participant", ["x1"]],
    ]);
  });
});

describe("resolveDownloadUrl", () => {
  it("prefixes API paths and keeps absolute URLs", () => {
    expect(resolveDownloadUrl("/v1/x?token=a", "https://api.test")).toBe(
      "https://api.test/v1/x?token=a",
    );
    expect(
      resolveDownloadUrl("https://s3.test/k?sig=1", "https://api.test"),
    ).toBe("https://s3.test/k?sig=1");
  });
});

describe("buildZipUrl", () => {
  it("appends each selected id", () => {
    expect(
      buildZipUrl(
        "/v1/transcripts/t1/download/zip?token=abc",
        ["summary", "track a"],
        "https://api.test",
      ),
    ).toBe(
      "https://api.test/v1/transcripts/t1/download/zip?token=abc&ids=summary&ids=track%20a",
    );
  });
});
