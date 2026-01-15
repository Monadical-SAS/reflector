import { useState } from "react";
import type { components } from "../../reflector-api";

type UpdateTranscript = components["schemas"]["UpdateTranscript"];
type GetTranscriptWithParticipants =
  components["schemas"]["GetTranscriptWithParticipants"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import {
  useTranscriptUpdate,
  useTranscriptParticipants,
} from "../../lib/apiHooks";
import { Heading, IconButton, Input, Flex, Spacer } from "@chakra-ui/react";
import { LuPen, LuCopy, LuCheck } from "react-icons/lu";
import ShareAndPrivacy from "./shareAndPrivacy";
import { buildTranscriptWithTopics } from "./buildTranscriptWithTopics";
import { toaster } from "../../components/ui/toaster";

type TranscriptTitle = {
  title: string;
  transcriptId: string;
  onUpdate: (newTitle: string) => void;

  // share props
  transcript: GetTranscriptWithParticipants | null;
  topics: GetTranscriptTopic[] | null;
  finalSummaryElement: HTMLDivElement | null;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  const [displayedTitle, setDisplayedTitle] = useState(props.title);
  const [preEditTitle, setPreEditTitle] = useState(props.title);
  const [isEditing, setIsEditing] = useState(false);
  const updateTranscriptMutation = useTranscriptUpdate();
  const participantsQuery = useTranscriptParticipants(
    props.transcript?.id || null,
  );

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
      props.onUpdate(newTitle);
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
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDisplayedTitle(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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
          {props.transcript && props.topics && (
            <>
              <IconButton
                aria-label="Copy Transcript"
                size="sm"
                variant="subtle"
                onClick={() => {
                  const text = buildTranscriptWithTopics(
                    props.topics || [],
                    participantsQuery?.data || null,
                    props.transcript?.title || null,
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
              <ShareAndPrivacy
                finalSummaryElement={props.finalSummaryElement}
                transcript={props.transcript}
                topics={props.topics}
              />
            </>
          )}
        </Flex>
      )}
    </>
  );
};

export default TranscriptTitle;
