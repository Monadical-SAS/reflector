import { useEffect, useRef, useState } from "react";
import React from "react";
import Markdown from "react-markdown";
import "../../../styles/markdown.css";
import {
  GetTranscript,
  GetTranscriptTopic,
  UpdateTranscript,
} from "../../../api";
import useApi from "../../../lib/useApi";
import {
  Flex,
  Heading,
  IconButton,
  Button,
  Textarea,
  Spacer,
} from "@chakra-ui/react";
import { FaPen } from "react-icons/fa";
import { useError } from "../../../(errors)/errorContext";
import ShareAndPrivacy from "../shareAndPrivacy";

type FinalSummaryProps = {
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
  onUpdate?: (newSummary) => void;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const finalSummaryRef = useRef<HTMLParagraphElement>(null);

  const [isEditMode, setIsEditMode] = useState(false);
  const [preEditSummary, setPreEditSummary] = useState("");
  const [editedSummary, setEditedSummary] = useState("");

  const api = useApi();

  const { setError } = useError();

  useEffect(() => {
    setEditedSummary(props.transcriptResponse?.long_summary || "");
  }, [props.transcriptResponse?.long_summary]);

  if (!props.topicsResponse || !props.transcriptResponse) {
    return null;
  }

  const updateSummary = async (newSummary: string, transcriptId: string) => {
    try {
      const requestBody: UpdateTranscript = {
        long_summary: newSummary,
      };
      const updatedTranscript = await api?.v1TranscriptUpdate({
        transcriptId,
        requestBody,
      });
      if (props.onUpdate) {
        props.onUpdate(newSummary);
      }
      console.log("Updated long summary:", updatedTranscript);
    } catch (err) {
      console.error("Failed to update long summary:", err);
      setError(err, "Failed to update long summary.");
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
    updateSummary(editedSummary, props.transcriptResponse.id);
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
    >
      <Flex dir="row" justify="start" align="center" wrap={"wrap-reverse"}>
        <Heading size={{ base: "md" }}>Summary</Heading>

        {isEditMode && (
          <>
            <Spacer />
            <Button
              onClick={onDiscardClick}
              colorScheme="gray"
              variant={"text"}
            >
              Discard
            </Button>
            <Button onClick={onSaveClick} colorScheme="blue">
              Save
            </Button>
          </>
        )}

        {!isEditMode && (
          <>
            <IconButton
              icon={<FaPen />}
              aria-label="Edit Summary"
              onClick={onEditClick}
            />
            <Spacer />
            <ShareAndPrivacy
              finalSummaryRef={finalSummaryRef}
              transcriptResponse={props.transcriptResponse}
              topicsResponse={props.topicsResponse}
            />
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
        <div ref={finalSummaryRef} className="markdown">
          <Markdown>{editedSummary}</Markdown>
        </div>
      )}
    </Flex>
  );
}
