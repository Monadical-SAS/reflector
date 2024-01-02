import { GetTranscript, GetTranscriptTopic } from "../api";
import { formatTime } from "./time";
import { extractDomain } from "./utils";

export async function sendZulipMessage(
  stream: string,
  topic: string,
  message: string,
) {
  console.log("Sendiing zulip message", stream, topic);
  try {
    const response = await fetch("/api/send-zulip-message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ stream, topic, message }),
    });
    return await response.json();
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}

export const ZULIP_MSG_MAX_LENGTH = 10000;

export function getZulipMessage(
  transcript: GetTranscript,
  topics: GetTranscriptTopic[] | null,
  includeTopics: boolean,
) {
  const date = new Date(transcript.created_at);

  // Get the timezone offset in minutes and convert it to hours and minutes
  const timezoneOffset = -date.getTimezoneOffset();
  const offsetHours = String(
    Math.floor(Math.abs(timezoneOffset) / 60),
  ).padStart(2, "0");
  const offsetMinutes = String(Math.abs(timezoneOffset) % 60).padStart(2, "0");
  const offsetSign = timezoneOffset >= 0 ? "+" : "-";

  // Combine to get the formatted timezone offset
  const formattedOffset = `${offsetSign}${offsetHours}:${offsetMinutes}`;

  // Now you can format your date and time string using this offset
  const formattedDate = date.toISOString().slice(0, 10);
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  const dateTimeString = `${formattedDate}T${hours}:${minutes}:${seconds}${formattedOffset}`;

  const domain = window.location.origin; // Gives you "http://localhost:3000" or your deployment base URL
  const link = `${domain}/transcripts/${transcript.id}`;

  let headerText = `# Reflector – ${transcript.title ?? "Unnamed recording"}

**Date**: <time:${dateTimeString}>
**Link**: [${extractDomain(link)}](${link})
**Duration**: ${formatTime(transcript.duration)}

`;
  let topicText = "";

  if (topics && includeTopics) {
    topicText = "```spoiler Topics\n";
    topics.forEach((topic) => {
      topicText += `1. [${formatTime(topic.timestamp)}] ${topic.title}\n`;
    });
    topicText += "```\n\n";
  }

  let summary = "```spoiler Summary\n";
  summary += transcript.long_summary;
  summary += "```\n\n";

  const message = headerText + summary + topicText + "-----\n";
  return message;
}
