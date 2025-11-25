import { useState } from "react";
import type { components } from "../../reflector-api";
type GetTranscript = components["schemas"]["GetTranscript"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import { Button, BoxProps, Box, Menu } from "@chakra-ui/react";
import { LuChevronDown } from "react-icons/lu";
import { client } from "../../lib/apiClient";
import { useTranscriptParticipants } from "../../lib/apiHooks";

type ShareCopyProps = {
  finalSummaryElement: HTMLDivElement | null;
  transcript: GetTranscript;
  topics: GetTranscriptTopic[];
};

export default function ShareCopy({
  finalSummaryElement,
  transcript,
  topics,
  ...boxProps
}: ShareCopyProps & BoxProps) {
  const [isCopiedSummary, setIsCopiedSummary] = useState(false);
  const [isCopiedTranscript, setIsCopiedTranscript] = useState(false);
  const [isCopying, setIsCopying] = useState(false);

  type TranscriptFormat = "text" | "text-timestamped" | "webvtt-named" | "json";

  const formatOptions: { value: TranscriptFormat; label: string }[] = [
    { value: "text", label: "Plain text" },
    { value: "text-timestamped", label: "Text + timestamps" },
    { value: "webvtt-named", label: "WebVTT (named)" },
    { value: "json", label: "JSON" },
  ];
  const participantsQuery = useTranscriptParticipants(transcript?.id || null);

  const onCopySummaryClick = () => {
    const text_to_copy = finalSummaryElement?.innerText;

    if (text_to_copy) {
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedSummary(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedSummary(false), 2000);
      });
    }
  };

  const onCopyTranscriptFormatClick = async (format: TranscriptFormat) => {
    try {
      setIsCopying(true);
      const { data, error } = await client.GET(
        "/v1/transcripts/{transcript_id}",
        {
          params: {
            path: { transcript_id: transcript.id },
            query: { transcript_format: format },
          },
        },
      );
      if (error) throw error;

      const transcriptData: any = data as any;
      const copiedText =
        format === "json"
          ? JSON.stringify(transcriptData?.transcript ?? {}, null, 2)
          : String(transcriptData?.transcript ?? "");

      if (copiedText) {
        await navigator.clipboard.writeText(copiedText);
        setIsCopiedTranscript(true);
        setTimeout(() => setIsCopiedTranscript(false), 2000);
      }
    } catch (e) {
      console.error("Failed to copy transcript:", e);
    } finally {
      setIsCopying(false);
    }
  };

  return (
    <Box {...boxProps}>
      <Menu.Root
        closeOnSelect={true}
        lazyMount={true}
        positioning={{ gutter: 4 }}
      >
        <Menu.Trigger asChild>
          <Button
            mr={2}
            variant="subtle"
            loading={isCopying}
            loadingText="Copying..."
          >
            {isCopiedTranscript ? "Copied!" : "Copy Transcript"}
            <LuChevronDown style={{ marginLeft: 6 }} />
          </Button>
        </Menu.Trigger>
        <Menu.Positioner>
          <Menu.Content>
            {formatOptions.map((opt) => (
              <Menu.Item
                key={opt.value}
                value={opt.value}
                _hover={{ backgroundColor: "gray.100" }}
                onClick={() => onCopyTranscriptFormatClick(opt.value)}
              >
                {opt.label}
              </Menu.Item>
            ))}
          </Menu.Content>
        </Menu.Positioner>
      </Menu.Root>
      <Button onClick={onCopySummaryClick} variant="subtle">
        {isCopiedSummary ? "Copied!" : "Copy Summary"}
      </Button>
    </Box>
  );
}
