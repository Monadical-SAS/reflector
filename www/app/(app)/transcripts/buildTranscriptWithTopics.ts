import type { components } from "../../reflector-api";
import { formatTime } from "../../lib/time";

type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
type Participant = components["schemas"]["Participant"];

function getSpeakerName(
  speakerNumber: number,
  participants?: Participant[] | null,
): string {
  const name = participants?.find((p) => p.speaker === speakerNumber)?.name;
  return name && name.trim().length > 0 ? name : `Speaker ${speakerNumber}`;
}

export function buildTranscriptWithTopics(
  topics: GetTranscriptTopic[],
  participants?: Participant[] | null,
  transcriptTitle?: string | null,
): string {
  const blocks: string[] = [];

  if (transcriptTitle && transcriptTitle.trim()) {
    blocks.push(`# ${transcriptTitle.trim()}`);
    blocks.push("");
  }

  for (const topic of topics) {
    // Topic header
    const topicTime = formatTime(Math.floor(topic.timestamp || 0));
    const title = topic.title?.trim() || "Untitled Topic";
    blocks.push(`## ${title} [${topicTime}]`);

    if (topic.segments && topic.segments.length > 0) {
      for (const seg of topic.segments) {
        const ts = formatTime(Math.floor(seg.start || 0));
        const speaker = getSpeakerName(seg.speaker as number, participants);
        const text = (seg.text || "").replace(/\s+/g, " ").trim();
        if (text) {
          blocks.push(`[${ts}] ${speaker}: ${text}`);
        }
      }
    } else if (topic.transcript) {
      // Fallback: plain transcript when segments are not present
      const text = topic.transcript.replace(/\s+/g, " ").trim();
      if (text) {
        blocks.push(text);
      }
    }

    // Blank line between topics
    blocks.push("");
  }

  // Trim trailing blank line
  while (blocks.length > 0 && blocks[blocks.length - 1] === "") {
    blocks.pop();
  }

  return blocks.join("\n");
}
