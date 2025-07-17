import React, { useState, useEffect } from "react";
import { formatTime } from "../../lib/time";
import ScrollToBottom from "./scrollToBottom";
import { Topic } from "./webSocketTypes";
import { generateHighContrastColor } from "../../lib/utils";
import useParticipants from "./useParticipants";
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Flex,
  Text,
} from "@chakra-ui/react";
import { featureEnabled } from "../../domainContext";

type TopicListProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  autoscroll: boolean;
  transcriptId: string;
  status: string;
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
    const topicDiv = document.getElementById(
      `accordion-button-topic-${activeTopic?.id}`,
    );

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
        padding={2}
      >
        {topics.length > 0 && (
          <Accordion
            index={topics.findIndex((topic) => topic.id == activeTopic?.id)}
            variant="custom"
            allowToggle
          >
            {topics.map((topic, index) => (
              <AccordionItem
                key={index}
                background={{
                  base: "light",
                  hover: "gray.100",
                  focus: "gray.100",
                }}
                id={`topic-${topic.id}`}
              >
                <Flex dir="row" letterSpacing={".2"}>
                  <AccordionButton
                    onClick={() => {
                      setActiveTopic(
                        activeTopic?.id == topic.id ? null : topic,
                      );
                    }}
                  >
                    <AccordionIcon />
                    <Box as="span" textAlign="left" ml="1">
                      {topic.title}{" "}
                      <Text
                        as="span"
                        color="gray.500"
                        fontSize="sm"
                        fontWeight="bold"
                      >
                        &nbsp;[{formatTime(topic.timestamp)}]&nbsp;-&nbsp;[
                        {formatTime(topic.timestamp + (topic.duration || 0))}]
                      </Text>
                    </Box>
                  </AccordionButton>
                </Flex>
                <AccordionPanel>
                  {topic.segments ? (
                    <>
                      {topic.segments.map((segment, index: number) => (
                        <Text
                          key={index}
                          className="text-left text-slate-500 text-sm md:text-base"
                          pb={2}
                          lineHeight={"1.3"}
                        >
                          <Text
                            as="span"
                            color={"gray.500"}
                            fontFamily={"monospace"}
                            fontSize={"sm"}
                          >
                            [{formatTime(segment.start)}]
                          </Text>
                          <Text
                            as="span"
                            fontWeight={"bold"}
                            fontSize={"sm"}
                            color={generateHighContrastColor(
                              `Speaker ${segment.speaker}`,
                              [96, 165, 250],
                            )}
                          >
                            {" "}
                            {getSpeakerName(segment.speaker)}:
                          </Text>{" "}
                          <span>{segment.text}</span>
                        </Text>
                      ))}
                    </>
                  ) : (
                    <>{topic.transcript}</>
                  )}
                </AccordionPanel>
              </AccordionItem>
            ))}
          </Accordion>
        )}

        {status == "recording" && (
          <Box textAlign={"center"}>
            <Text>{currentTranscriptText}</Text>
          </Box>
        )}
        {(status == "recording" || status == "idle") &&
          currentTranscriptText.length == 0 &&
          topics.length == 0 && (
            <Box textAlign={"center"} textColor="gray">
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
          <Box textAlign={"center"} textColor="gray">
            <Text>We are processing the recording, please wait.</Text>
            {!requireLogin && (
              <span>
                Please do not navigate away from the page during this time.
              </span>
            )}
          </Box>
        )}
        {status == "ended" && topics.length == 0 && (
          <Box textAlign={"center"} textColor="gray">
            <Text>Recording has ended without topics being found.</Text>
          </Box>
        )}
        {status == "error" && (
          <Box textAlign={"center"} textColor="gray">
            <Text>There was an error processing your recording</Text>
          </Box>
        )}
      </Box>
    </Flex>
  );
}
