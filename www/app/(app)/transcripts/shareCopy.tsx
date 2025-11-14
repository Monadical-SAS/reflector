import { useState } from "react";
import type { components } from "../../reflector-api";
type GetTranscript = components["schemas"]["GetTranscript"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import { Button, BoxProps, Box } from "@chakra-ui/react";
import { buildTranscriptWithTopics } from "./buildTranscriptWithTopics";
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
  const participantsQuery = useTranscriptParticipants(
    transcriptResponse?.id || null,
  );

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
    const text_to_copy =
      buildTranscriptWithTopics(
        topics || [],
        participantsQuery?.data || null,
        transcript?.title || null,
      ) || "";

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
