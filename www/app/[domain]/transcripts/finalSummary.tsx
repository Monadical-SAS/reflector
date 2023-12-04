import { useRef, useState } from "react";
import React from "react";
import Markdown from "react-markdown";
import "../../styles/markdown.css";
import getApi from "../../lib/getApi";

type FinalSummaryProps = {
  summary: string;
  fullTranscript: string;
  transcriptId: string;
  openZulipModal: () => void;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const finalSummaryRef = useRef<HTMLParagraphElement>(null);
  const [isCopiedSummary, setIsCopiedSummary] = useState(false);
  const [isCopiedTranscript, setIsCopiedTranscript] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [preEditSummary, setPreEditSummary] = useState(props.summary);
  const [editedSummary, setEditedSummary] = useState(props.summary);
  const api = getApi();

  const updateSummary = async (newSummary: string, transcriptId: string) => {
    if (!api) return;
    try {
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
    let text_to_copy = props.fullTranscript;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedTranscript(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedTranscript(false), 2000);
      });
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
                className={
                  "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
                }
                onClick={() => props.openZulipModal()}
              >
                <span className="text-xs">➡️ Zulip</span>
              </button>
              <button
                onClick={onEditClick}
                className={
                  "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
                }
              >
                <span className="text-xs">✏️ Summary</span>
              </button>
              <button
                onClick={onCopyTranscriptClick}
                className={
                  (isCopiedTranscript ? "bg-blue-500" : "bg-blue-400") +
                  " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
                }
                style={{ minHeight: "30px" }}
              >
                <span className="text-xs">
                  {isCopiedTranscript ? "Copied!" : "Copy Transcript"}
                </span>
              </button>
              <button
                onClick={onCopySummaryClick}
                className={
                  (isCopiedSummary ? "bg-blue-500" : "bg-blue-400") +
                  " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
                }
                style={{ minHeight: "30px" }}
              >
                <span className="text-xs">
                  {isCopiedSummary ? "Copied!" : "Copy Summary"}
                </span>
              </button>
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
        <p ref={finalSummaryRef} className="markdown">
          <Markdown>{editedSummary}</Markdown>
        </p>
      )}
    </div>
  );
}
