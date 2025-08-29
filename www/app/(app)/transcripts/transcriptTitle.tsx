import { useState } from "react";
import type { components } from "../../reflector-api";

type UpdateTranscript = components["schemas"]["UpdateTranscript"];
import { useTranscriptUpdate } from "../../lib/api-hooks";
import { Heading, IconButton, Input, Flex, Spacer } from "@chakra-ui/react";
import { LuPen } from "react-icons/lu";

type TranscriptTitle = {
  title: string;
  transcriptId: string;
  onUpdate?: (newTitle: string) => void;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  const [displayedTitle, setDisplayedTitle] = useState(props.title);
  const [preEditTitle, setPreEditTitle] = useState(props.title);
  const [isEditing, setIsEditing] = useState(false);
  const updateTranscriptMutation = useTranscriptUpdate();

  const updateTitle = async (newTitle: string, transcriptId: string) => {
    try {
      const requestBody: UpdateTranscript = {
        title: newTitle,
      };
      await updateTranscriptMutation.mutateAsync({
        params: {
          path: { transcript_id: transcriptId },
        },
        body: requestBody,
      });
      if (props.onUpdate) {
        props.onUpdate(newTitle);
      }
      console.log("Updated transcript title:", newTitle);
    } catch (err) {
      console.error("Failed to update transcript:", err);
      // Revert title on error
      setDisplayedTitle(preEditTitle);
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
        <Flex alignItems="center">
          <Heading
            onClick={handleTitleClick}
            cursor={"pointer"}
            size={"lg"}
            lineClamp={1}
            pr={2}
          >
            {displayedTitle}
          </Heading>
          <Spacer />
          <IconButton
            aria-label="Edit Transcript Title"
            onClick={handleTitleClick}
            size="sm"
            variant="subtle"
          >
            <LuPen />
          </IconButton>
        </Flex>
      )}
    </>
  );
};

export default TranscriptTitle;
