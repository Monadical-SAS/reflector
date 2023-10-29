import { useRef, useState } from "react";
import React from "react";
import Markdown from "react-markdown";
import "../../styles/markdown.css";
import getApi from "../../lib/getApi";

type FinalSummaryProps = {
  protectedPath: boolean;
  summary: string;
  fullTranscript: string;
  transcriptId: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const finalSummaryRef = useRef<HTMLParagraphElement>(null);
  const [isCopiedSummary, setIsCopiedSummary] = useState(false);
  const [isCopiedTranscript, setIsCopiedTranscript] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedSummary, setEditedSummary] = useState(props.summary);
  const api = getApi(props.protectedPath);

  const updateSummary = async (newSummary: string, transcriptId: string) => {
    try {
      setEditedSummary(newSummary);
      const updatedTranscript = await api.v1TranscriptUpdate({
        transcriptId,
        updateTranscript: {
          longSummary: newSummary,
        },
      });
      console.log("Updated long summary:", updatedTranscript);
    } catch (err) {
      console.error("Failed to update long summary:", err);
    }
  };

  const handleCopySummaryClick = () => {
    let text_to_copy = finalSummaryRef.current?.innerText;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedSummary(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedSummary(false), 2000);
      });
  };

  const handleCopyTranscriptClick = () => {
    let text_to_copy = props.fullTranscript;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedTranscript(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedTranscript(false), 2000);
      });
  };

  const handleEditMode = () => {
    setIsEditMode(!isEditMode);
  };

  return (
    <div className="overflow-y-auto h-auto max-h-full">
      <div className="flex flex-row flex-wrap-reverse justify-between items-center">
        <h2 className="text-lg sm:text-xl md:text-2xl font-bold">
          Final Summary
        </h2>
        <div className="ml-auto flex space-x-2 mb-2">
          <button
            onClick={handleEditMode}
            className={
              "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
            }
          >
            {isEditMode ? "Save" : "Edit Summary"}
          </button>
          <button
            onClick={handleCopyTranscriptClick}
            className={
              (isCopiedTranscript ? "bg-blue-500" : "bg-blue-400") +
              " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
            }
            style={{ minHeight: "30px" }}
          >
            {isCopiedTranscript ? "Copied!" : "Copy Full Transcript"}
          </button>
          <button
            onClick={handleCopySummaryClick}
            className={
              (isCopiedSummary ? "bg-blue-500" : "bg-blue-400") +
              " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
            }
            style={{ minHeight: "30px" }}
          >
            {isCopiedSummary ? "Copied!" : "Copy Summary"}
          </button>
        </div>
      </div>
      {isEditMode ? (
        <textarea
          value={editedSummary}
          onChange={(e) => updateSummary(e.target.value, props.transcriptId)}
          className="markdown"
        />
      ) : (
        <p ref={finalSummaryRef} className="markdown">
          <Markdown>{editedSummary}</Markdown>
        </p>
      )}{" "}
    </div>
  );
}
