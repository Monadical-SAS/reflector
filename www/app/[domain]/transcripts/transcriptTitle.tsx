import { useState } from "react";
import getApi from "../../lib/getApi";

type TranscriptTitle = {
  protectedPath: boolean;
  title: string;
  transcriptId: string;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  const [currentTitle, setCurrentTitle] = useState(props.title);
  const api = getApi(props.protectedPath);

  const updateTitle = async (newTitle: string, transcriptId: string) => {
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
  const handleClick = () => {
    const newTitle = prompt("Please enter the new title:", currentTitle);
    if (newTitle !== null) {
      setCurrentTitle(newTitle);
      updateTitle(newTitle, props.transcriptId);
    }
  };

  return (
    <h2
      className="text-2xl lg:text-4xl font-extrabold text-center mb-4"
      onClick={handleClick}
    >
      {currentTitle}
    </h2>
  );
};

export default TranscriptTitle;
