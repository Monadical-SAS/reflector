import { useEffect, useRef, useState } from "react";
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
import { LuPen, LuCopy, LuCheck } from "react-icons/lu";
import { buildTranscriptWithTopics } from "../buildTranscriptWithTopics";
import { useTranscriptParticipants } from "../../../lib/apiHooks";
import { toaster } from "../../../components/ui/toaster";
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

  const { setError } = useError();
  const updateTranscriptMutation = useTranscriptUpdate();
  const participantsQuery = useTranscriptParticipants(
    props.transcriptResponse?.id || null,
  );

  useEffect(() => {
    setEditedSummary(props.transcriptResponse?.long_summary || "");
  }, [props.transcriptResponse?.long_summary]);

  if (!props.topicsResponse || !props.transcriptResponse) {
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
      if (props.onUpdate) {
        props.onUpdate(newSummary);
      }
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
              aria-label="Copy Transcript"
              size="sm"
              variant="subtle"
              onClick={() => {
                const text = buildTranscriptWithTopics(
                  props.topicsResponse || [],
                  participantsQuery?.data || null,
                  props.transcriptResponse?.title || null,
                );
                if (!text) return;
                navigator.clipboard
                  .writeText(text)
                  .then(() => {
                    toaster
                      .create({
                        placement: "top",
                        duration: 2500,
                        render: () => (
                          <div className="chakra-ui-light">
                            <div
                              style={{
                                background: "#38A169",
                                color: "white",
                                padding: "8px 12px",
                                borderRadius: 6,
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                boxShadow: "rgba(0,0,0,0.25) 0px 4px 12px",
                              }}
                            >
                              <LuCheck /> Transcript copied
                            </div>
                          </div>
                        ),
                      })
                      .then(() => {});
                  })
                  .catch(() => {});
              }}
            >
              <LuCopy />
            </IconButton>
            <IconButton
              aria-label="Edit Summary"
              onClick={onEditClick}
              size="sm"
              variant="subtle"
            >
              <LuPen />
            </IconButton>
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
