import { useState } from "react";
import type { components } from "../../reflector-api";
type GetTranscript = components["schemas"]["GetTranscript"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import { Button, BoxProps, Box } from "@chakra-ui/react";

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

  const onCopyTranscriptClick = () => {
    let text_to_copy =
      topics
        ?.map((topic) => topic.transcript)
        .join("\n\n")
        .replace(/ +/g, " ")
        .trim() || "";

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedTranscript(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedTranscript(false), 2000);
      });
  };

  return (
    <Box {...boxProps}>
      <Button onClick={onCopyTranscriptClick} mr={2} variant="subtle">
        {isCopiedTranscript ? "Copied!" : "Copy Transcript"}
      </Button>
      <Button onClick={onCopySummaryClick} variant="subtle">
        {isCopiedSummary ? "Copied!" : "Copy Summary"}
      </Button>
    </Box>
  );
}
