import { useEffect, useRef, useState } from "react";
import React from "react";
import Markdown from "react-markdown";
import "../../../styles/markdown.css";
import { UpdateTranscript } from "../../../api";
import useApi from "../../../lib/useApi";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import { Box, Flex, IconButton, Modal, ModalContent } from "@chakra-ui/react";
import { FaShare } from "react-icons/fa";
import ShareTranscript from "../shareTranscript";

type FinalSummaryProps = {
  transcriptId: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const transcript = useTranscript(props.transcriptId);
  const topics = useTopics(props.transcriptId);

  const finalSummaryRef = useRef<HTMLParagraphElement>(null);

  const [isEditMode, setIsEditMode] = useState(false);
  const [preEditSummary, setPreEditSummary] = useState("");
  const [editedSummary, setEditedSummary] = useState("");

  const [showShareModal, setShowShareModal] = useState(false);

  useEffect(() => {
    setEditedSummary(transcript.response?.long_summary || "");
  }, [transcript.response?.long_summary]);

  if (!topics.topics || !transcript.response) {
    return null;
  }

  const updateSummary = async (newSummary: string, transcriptId: string) => {
    try {
      const api = useApi();
      const requestBody: UpdateTranscript = {
        long_summary: newSummary,
      };
      const updatedTranscript = await api?.v1TranscriptUpdate(
        transcriptId,
        requestBody,
      );
      console.log("Updated long summary:", updatedTranscript);
    } catch (err) {
      console.error("Failed to update long summary:", err);
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
    updateSummary(editedSummary, props.transcriptId);
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
    <div
      className={
        (isEditMode ? "overflow-y-none" : "overflow-y-auto") +
        " max-h-full flex flex-col h-full"
      }
    >
      <div className="flex flex-row flex-wrap-reverse justify-between items-center">
        <h2 className="text-lg sm:text-xl md:text-2xl font-bold">
          Final Summary
        </h2>

        <div className="ml-auto flex space-x-2 mb-2">
          {isEditMode && (
            <>
              <button
                onClick={onDiscardClick}
                className={"text-gray-500 text-sm hover:underline"}
              >
                Discard Changes
              </button>
              <button
                onClick={onSaveClick}
                className={
                  "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
                }
              >
                Save Changes
              </button>
            </>
          )}

          {!isEditMode && (
            <>
              <button
                onClick={onEditClick}
                className={
                  "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
                }
              >
                <span className="text-xs">✏️ Summary</span>
              </button>
              <IconButton
                icon={<FaShare />}
                onClick={() => setShowShareModal(true)}
                aria-label="Share"
              />
              {showShareModal && (
                <Modal
                  isOpen={showShareModal}
                  onClose={() => setShowShareModal(false)}
                  size="xl"
                >
                  <ModalContent>
                    <ShareTranscript
                      finalSummaryRef={finalSummaryRef}
                      transcriptResponse={transcript.response}
                      topicsResponse={topics.topics}
                    />
                  </ModalContent>
                </Modal>
              )}
            </>
          )}
        </div>
      </div>

      {isEditMode ? (
        <div className="flex-grow overflow-y-none">
          <textarea
            value={editedSummary}
            onChange={(e) => setEditedSummary(e.target.value)}
            className="markdown w-full h-full d-block p-2 border rounded shadow-sm"
            onKeyDown={(e) => handleTextAreaKeyDown(e)}
          />
        </div>
      ) : (
        <div ref={finalSummaryRef} className="markdown">
          <Markdown>{editedSummary}</Markdown>
        </div>
      )}
    </div>
  );
}
