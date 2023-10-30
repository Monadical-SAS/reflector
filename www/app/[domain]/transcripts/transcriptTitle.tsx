import { useState } from "react";
import getApi from "../../lib/getApi";

type TranscriptTitle = {
  protectedPath: boolean;
  title: string;
  transcriptId: string;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  const [displayedTitle, setDisplayedTitle] = useState(props.title);
  const [preEditTitle, setPreEditTitle] = useState(props.title);
  const [isEditing, setIsEditing] = useState(false);
  const api = getApi(props.protectedPath);

  const updateTitle = async (newTitle: string, transcriptId: string) => {
    if (!api) return;
    try {
      const updatedTranscript = await api.v1TranscriptUpdate({
        transcriptId,
        updateTranscript: {
          title: newTitle,
        },
      });
      console.log("Updated transcript:", updatedTranscript);
    } catch (err) {
      console.error("Failed to update transcript:", err);
    }
  };

  const handleTitleClick = () => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

    if (isMobile) {
      // Use prompt
      const newTitle = prompt("Please enter the new title:", displayedTitle);
      if (newTitle !== null) {
        setDisplayedTitle(newTitle);
        updateTitle(newTitle, props.transcriptId);
      }
    } else {
      setPreEditTitle(displayedTitle);
      setIsEditing(true);
    }
  };

  const handleChange = (e) => {
    setDisplayedTitle(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      updateTitle(displayedTitle, props.transcriptId);
      setIsEditing(false);
    } else if (e.key === "Escape") {
      setDisplayedTitle(preEditTitle);
      setIsEditing(false);
    }
  };

  return (
    <>
      {isEditing ? (
        <input
          type="text"
          value={displayedTitle}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          autoFocus
          className="text-2xl lg:text-4xl font-extrabold text-center mb-4 w-full border-none bg-transparent overflow-hidden h-[fit-content]"
        />
      ) : (
        <h2
          className="text-2xl lg:text-4xl font-extrabold text-center mb-4 cursor-pointer"
          onClick={handleTitleClick}
        >
          {displayedTitle}
        </h2>
      )}
    </>
  );
};

export default TranscriptTitle;
