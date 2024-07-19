import { useState } from "react";
import { UpdateTranscript } from "../../api";
import useApi from "../../lib/useApi";
import { Heading, IconButton, Input } from "@chakra-ui/react";
import { FaPen } from "react-icons/fa";

type TranscriptTitle = {
  title: string;
  transcriptId: string;
  onUpdate?: (newTitle: string) => void;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  const [displayedTitle, setDisplayedTitle] = useState(props.title);
  const [preEditTitle, setPreEditTitle] = useState(props.title);
  const [isEditing, setIsEditing] = useState(false);
  const api = useApi();

  const updateTitle = async (newTitle: string, transcriptId: string) => {
    if (!api) return;
    try {
      const requestBody: UpdateTranscript = {
        title: newTitle,
      };
      const updatedTranscript = await api?.v1TranscriptUpdate({
        transcriptId,
        requestBody,
      });
      if (props.onUpdate) {
        props.onUpdate(newTitle);
      }
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

  const handleBlur = () => {
    if (displayedTitle !== preEditTitle) {
      updateTitle(displayedTitle, props.transcriptId);
    }
    setIsEditing(false);
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
        <Input
          type="text"
          value={displayedTitle}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          autoFocus
          onBlur={handleBlur}
          size={"lg"}
          fontSize={"xl"}
          fontWeight={"bold"}
          // className="text-2xl lg:text-4xl font-extrabold text-center mb-4 w-full border-none bg-transparent overflow-hidden h-[fit-content]"
        />
      ) : (
        <>
          <Heading
            // className="text-2xl lg:text-4xl font-extrabold text-center mb-4 cursor-pointer"
            onClick={handleTitleClick}
            cursor={"pointer"}
            size={"lg"}
            noOfLines={1}
          >
            {displayedTitle}
          </Heading>
          <IconButton
            icon={<FaPen />}
            aria-label="Edit Transcript Title"
            onClick={handleTitleClick}
            fontSize={"15px"}
          />
        </>
      )}
    </>
  );
};

export default TranscriptTitle;
