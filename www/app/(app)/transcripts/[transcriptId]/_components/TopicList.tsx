import React, { useState, useEffect } from "react";
import ScrollToBottom from "../../scrollToBottom";
import { Topic } from "../../webSocketTypes";
import useParticipants from "../../useParticipants";
import { Box, Flex, Text, Accordion } from "@chakra-ui/react";
import { TopicItem } from "./TopicItem";
import { TranscriptStatus } from "../../../../lib/transcript";

import { featureEnabled } from "../../../../lib/features";

type TopicListProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  autoscroll: boolean;
  transcriptId: string;
  status: TranscriptStatus | null;
  currentTranscriptText: any;
};

export function TopicList({
  topics,
  useActiveTopic,
  autoscroll,
  transcriptId,
  status,
  currentTranscriptText,
}: TopicListProps) {
  const [activeTopic, setActiveTopic] = useActiveTopic;
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);
  const participants = useParticipants(transcriptId);

  const scrollToTopic = () => {
    const topicDiv = document.getElementById(`topic-${activeTopic?.id}`);

    setTimeout(() => {
      topicDiv?.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });
    }, 200);
  };

  useEffect(() => {
    if (activeTopic && autoscroll) scrollToTopic();
  }, [activeTopic, autoscroll]);

  // scroll top is not rounded, heights are, so exact match won't work.
  // https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollHeight#determine_if_an_element_has_been_totally_scrolled
  const toggleScroll = (element) => {
    const bottom =
      Math.abs(
        element.scrollHeight - element.clientHeight - element.scrollTop,
      ) < 2 || element.scrollHeight == element.clientHeight;
    if (!bottom && autoscrollEnabled) {
      setAutoscrollEnabled(false);
    } else if (bottom && !autoscrollEnabled) {
      setAutoscrollEnabled(true);
    }
  };
  const handleScroll = (e) => {
    toggleScroll(e.target);
  };

  useEffect(() => {
    if (autoscroll) {
      const topicsDiv = document.getElementById("scroll-div");

      topicsDiv && toggleScroll(topicsDiv);
    }
  }, [activeTopic, autoscroll]);

  useEffect(() => {
    if (autoscroll && autoscrollEnabled) scrollToBottom();
  }, [topics.length, currentTranscriptText]);

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById("scroll-div");

    if (topicsDiv) topicsDiv.scrollTop = topicsDiv.scrollHeight;
  };

  const getSpeakerName = (speakerNumber: number) => {
    if (!participants.response) return;
    return (
      participants.response.find(
        (participant) => participant.speaker == speakerNumber,
      )?.name || `Speaker ${speakerNumber}`
    );
  };

  const requireLogin = featureEnabled("requireLogin");

  useEffect(() => {
    if (autoscroll) {
      setActiveTopic(topics[topics.length - 1]);
    }
  }, [topics, autoscroll]);

  return (
    <Flex
      position={"relative"}
      w={"100%"}
      h={"95%"}
      flexDirection={"column"}
      justify={"center"}
      align={"center"}
      flexShrink={0}
    >
      {autoscroll && (
        <ScrollToBottom
          visible={!autoscrollEnabled}
          handleScrollBottom={scrollToBottom}
        />
      )}

      <Box
        id="scroll-div"
        overflowY={"auto"}
        h={"100%"}
        onScroll={handleScroll}
        width="full"
      >
        {topics.length > 0 && (
          <Accordion.Root
            multiple={false}
            collapsible={true}
            value={activeTopic ? [activeTopic.id] : []}
            onValueChange={(details) => {
              const selectedTopicId = details.value[0];
              const selectedTopic = selectedTopicId
                ? topics.find((t) => t.id === selectedTopicId)
                : null;
              setActiveTopic(selectedTopic || null);
            }}
          >
            {topics.map((topic) => (
              <TopicItem
                key={topic.id}
                topic={topic}
                isActive={activeTopic?.id === topic.id}
                getSpeakerName={getSpeakerName}
              />
            ))}
          </Accordion.Root>
        )}

        {status == "recording" && (
          <Box textAlign={"center"}>
            <Text>{currentTranscriptText}</Text>
          </Box>
        )}
        {(status == "recording" || status == "idle") &&
          currentTranscriptText.length == 0 &&
          topics.length == 0 && (
            <Box textAlign={"center"} color="gray">
              <Text>
                Full discussion transcript will appear here after you start
                recording.
              </Text>
              <Text>
                It may take up to 5 minutes of conversation to first appear.
              </Text>
            </Box>
          )}
        {status == "processing" && (
          <Box textAlign={"center"} color="gray">
            <Text>We are processing the recording, please wait.</Text>
            {!requireLogin && (
              <span>
                Please do not navigate away from the page during this time.
              </span>
            )}
          </Box>
        )}
        {status == "ended" && topics.length == 0 && (
          <Box textAlign={"center"} color="gray">
            <Text>Recording has ended without topics being found.</Text>
          </Box>
        )}
        {status == "error" && (
          <Box textAlign={"center"} color="gray">
            <Text>There was an error processing your recording</Text>
          </Box>
        )}
      </Box>
    </Flex>
  );
}
