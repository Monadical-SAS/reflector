import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronDown,
} from "@fortawesome/free-solid-svg-icons";
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
  Icon,
  Text,
} from "@chakra-ui/react";
import { FaChevronDown, FaChevronRight } from "react-icons/fa";

type TopicListProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  autoscroll: boolean;
  transcriptId: string;
};

export function TopicList({
  topics,
  useActiveTopic,
  autoscroll,
  transcriptId,
}: TopicListProps) {
  const [activeTopic, setActiveTopic] = useActiveTopic;
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);
  const participants = useParticipants(transcriptId);

  useEffect(() => {
    if (autoscroll && autoscrollEnabled) scrollToBottom();
  }, [topics.length]);

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById("topics-div");

    if (topicsDiv) topicsDiv.scrollTop = topicsDiv.scrollHeight;
  };

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
      const topicsDiv = document.getElementById("topics-div");

      topicsDiv && toggleScroll(topicsDiv);
    }
  }, [activeTopic, autoscroll]);

  const getSpeakerName = (speakerNumber: number) => {
    if (!participants.response) return;
    return (
      participants.response.find(
        (participant) => participant.speaker == speakerNumber,
      )?.name || `Speaker ${speakerNumber}`
    );
  };

  return (
    <Flex
      position={"relative"}
      w={"100%"}
      h={"100%"}
      dir="column"
      justify={"center"}
      align={"center"}
    >
      {topics.length > 0 ? (
        <>
          {autoscroll && (
            <ScrollToBottom
              visible={!autoscrollEnabled}
              handleScrollBottom={scrollToBottom}
            />
          )}

          <Accordion
            id="topics-div"
            overflowY={"auto"}
            h={"100%"}
            onScroll={handleScroll}
            defaultIndex={[
              topics.findIndex((topic) => topic.id == activeTopic?.id),
            ]}
            variant="custom"
            allowToggle
          >
            {topics.map((topic, index) => (
              <AccordionItem
                key={index}
                background={{
                  base: "light",
                  _hover: "gray.100",
                  _focus: "gray.100",
                }}
                padding={2}
                onClick={() => {
                  setActiveTopic(activeTopic?.id == topic.id ? null : topic);
                }}
              >
                <Flex dir="row" letterSpacing={".2"}>
                  <AccordionButton>
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
                          <span className="font-mono text-slate-500">
                            [{formatTime(segment.start)}]
                          </span>
                          <span
                            className="font-bold text-slate-500"
                            style={{
                              color: generateHighContrastColor(
                                `Speaker ${segment.speaker}`,
                                [96, 165, 250],
                              ),
                            }}
                          >
                            {" "}
                            {getSpeakerName(segment.speaker)}:
                          </span>{" "}
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
        </>
      ) : (
        <Box textAlign={"center"} textColor="gray">
          <Text>
            Discussion topics will appear here after you start recording.
          </Text>
          <Text>
            It may take up to 5 minutes of conversation for the first topic to
            appear.
          </Text>
        </Box>
      )}
    </Flex>
  );
}
