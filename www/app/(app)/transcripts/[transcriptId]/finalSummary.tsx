import { useEffect, useState } from "react";
import React from "react";
import Markdown from "react-markdown";
import "../../../styles/markdown.css";
import type { components } from "../../../reflector-api";
type GetTranscript = components["schemas"]["GetTranscript"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import { useTranscriptUpdate } from "../../../lib/apiHooks";
import {
  Flex,
  Heading,
  IconButton,
  Button,
  Textarea,
  Spacer,
} from "@chakra-ui/react";
import { LuPen } from "react-icons/lu";
import { useError } from "../../../(errors)/errorContext";

type FinalSummaryProps = {
  transcript: GetTranscript;
  topics: GetTranscriptTopic[];
  onUpdate: (newSummary: string) => void;
  finalSummaryRef: React.Dispatch<React.SetStateAction<HTMLDivElement | null>>;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const [isEditMode, setIsEditMode] = useState(false);
  const [preEditSummary, setPreEditSummary] = useState("");
  const [editedSummary, setEditedSummary] = useState("");

  const { setError } = useError();
  const updateTranscriptMutation = useTranscriptUpdate();

  useEffect(() => {
    setEditedSummary(props.transcript?.long_summary || "");
  }, [props.transcript?.long_summary]);

  if (!props.topics || !props.transcript) {
    return null;
  }

  const updateSummary = async (newSummary: string, transcriptId: string) => {
    try {
      const updatedTranscript = await updateTranscriptMutation.mutateAsync({
        params: {
          path: {
            transcript_id: transcriptId,
          },
        },
        body: {
          long_summary: newSummary,
        },
      });
      props.onUpdate(newSummary);
      console.log("Updated long summary:", updatedTranscript);
    } catch (err) {
      console.error("Failed to update long summary:", err);
      setError(err as Error, "Failed to update long summary.");
    }
  };

  const onEditClick = () => {
    setPreEditSummary(editedSummary);
    setIsEditMode(true);
  };

  const onDiscardClick = () => {
    setEditedSummary(preEditSummary);
    setIsEditMode(false);
  };

  const onSaveClick = () => {
    updateSummary(editedSummary, props.transcript.id);
    setIsEditMode(false);
  };

  const handleTextAreaKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onDiscardClick();
    }

    if (e.key === "Enter" && e.shiftKey) {
      onSaveClick();
      e.preventDefault(); // prevent the default action of adding a new line
    }
  };

  return (
    <Flex
      direction="column"
      maxH={"100%"}
      h={"100%"}
      overflowY={isEditMode ? "hidden" : "auto"}
      pb={4}
      position="relative"
    >
      <Flex
        dir="row"
        justify="start"
        align="center"
        wrap={"wrap-reverse"}
        position={isEditMode ? "inherit" : "absolute"}
        right="0"
      >
        {isEditMode && (
          <Flex gap={2} align="center" w="full">
            <Heading size={{ base: "md" }}>Summary</Heading>
            <Spacer />
            <Button onClick={onDiscardClick} variant="ghost">
              Cancel
            </Button>
            <Button
              onClick={onSaveClick}
              disabled={updateTranscriptMutation.isPending}
            >
              Save
            </Button>
          </Flex>
        )}
        {!isEditMode && (
          <>
            <Spacer />
            <IconButton
              aria-label="Edit Summary"
              onClick={onEditClick}
              size="sm"
              variant="subtle"
            >
              <LuPen />
            </IconButton>
          </>
        )}
      </Flex>

      {isEditMode ? (
        <Textarea
          value={editedSummary}
          onChange={(e) => setEditedSummary(e.target.value)}
          className="markdown"
          onKeyDown={(e) => handleTextAreaKeyDown(e)}
          h={"100%"}
          resize={"none"}
          mt={2}
        />
      ) : (
        <div ref={props.finalSummaryRef} className="markdown">
          <Markdown>{editedSummary}</Markdown>
        </div>
      )}
    </Flex>
  );
}
