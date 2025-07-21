import { useState } from "react";
import { GetTranscript, GetTranscriptTopic } from "../../api";
import { Button, BoxProps, Box } from "@chakra-ui/react";

type ShareCopyProps = {
  finalSummaryRef: any;
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
};

export default function ShareCopy({
  finalSummaryRef,
  transcriptResponse,
  topicsResponse,
  ...boxProps
}: ShareCopyProps & BoxProps) {
  const [isCopiedSummary, setIsCopiedSummary] = useState(false);
  const [isCopiedTranscript, setIsCopiedTranscript] = useState(false);

  const onCopySummaryClick = () => {
    let text_to_copy = finalSummaryRef.current?.innerText;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedSummary(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedSummary(false), 2000);
      });
  };

  const onCopyTranscriptClick = () => {
    let text_to_copy =
      topicsResponse
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
