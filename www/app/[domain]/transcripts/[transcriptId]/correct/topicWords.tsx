import { Dispatch, SetStateAction, useEffect } from "react";
import { UseParticipants } from "../../useParticipants";
import { UseTopicWithWords } from "../../useTopicWithWords";
import { TimeSlice, selectedTextIsTimeSlice } from "./types";
import { BoxProps, Box, Container, Text, Spinner } from "@chakra-ui/react";

type TopicWordsProps = {
  stateSelectedText: [
    number | TimeSlice | undefined,
    Dispatch<SetStateAction<number | TimeSlice | undefined>>,
  ];
  participants: UseParticipants;
  topicWithWords: UseTopicWithWords;
};

const topicWords = ({
  stateSelectedText,
  participants,
  topicWithWords,
  ...chakraProps
}: TopicWordsProps & BoxProps) => {
  const [selectedText, setSelectedText] = stateSelectedText;

  useEffect(() => {
    if (topicWithWords.loading && selectedTextIsTimeSlice(selectedText)) {
      setSelectedText(undefined);
    }
  }, [topicWithWords.loading]);

  const getStartTimeFromFirstNode = (node, offset, reverse) => {
    // Check if the current node represents a word with a start time
    if (node.parentElement?.dataset["start"]) {
      // Check if the position is at the end of the word
      if (node.textContent?.length == offset) {
        // Try to get the start time of the next word
        const nextWordStartTime =
          node.parentElement.nextElementSibling?.dataset["start"];
        if (nextWordStartTime) {
          return nextWordStartTime;
        }

        // If no next word, get start of the first word in the next paragraph
        const nextParaFirstWordStartTime =
          node.parentElement.parentElement.nextElementSibling?.childNodes[1]
            ?.dataset["start"];
        if (nextParaFirstWordStartTime) {
          return nextParaFirstWordStartTime;
        }

        // Return default values based on 'reverse' flag
        // If reverse is false, means the node is the last word of the topic transcript,
        // so reverse should be true, and we set a high value to make sure this is not picked as the start time.
        // Reverse being true never happens given how we use this function, but for consistency in case things change,
        // we set a low value.
        return reverse ? 0 : 9999999999999;
      } else {
        // Position is within the word, return start of this word
        return node.parentElement.dataset["start"];
      }
    } else {
      // Selection is on a name, return start of the next word
      return node.parentElement.nextElementSibling?.dataset["start"];
    }
  };

  const onMouseUp = (e) => {
    let selection = window.getSelection();
    if (
      selection &&
      selection.anchorNode &&
      selection.focusNode &&
      selection.anchorNode == selection.focusNode &&
      selection.anchorOffset == selection.focusOffset
    ) {
      setSelectedText(undefined);
      selection.empty();
      return;
    }
    if (
      selection &&
      selection.anchorNode &&
      selection.focusNode &&
      (selection.anchorNode !== selection.focusNode ||
        selection.anchorOffset !== selection.focusOffset)
    ) {
      const anchorNode = selection.anchorNode;
      const anchorIsWord =
        !!selection.anchorNode.parentElement?.dataset["start"];
      const focusNode = selection.focusNode;
      const focusIsWord = !!selection.focusNode.parentElement?.dataset["end"];

      // If selected a speaker :
      if (
        !anchorIsWord &&
        !focusIsWord &&
        anchorNode.parentElement == focusNode.parentElement
      ) {
        setSelectedText(
          focusNode.parentElement?.dataset["speaker"]
            ? parseInt(focusNode.parentElement?.dataset["speaker"])
            : undefined,
        );
        return;
      }

      const anchorStart = getStartTimeFromFirstNode(
        anchorNode,
        selection.anchorOffset,
        false,
      );
      // if selection end on a word, we get the end time from the span that contains it
      const focusEnd =
        selection.focusOffset !== 0
          ? selection.focusNode.parentElement?.dataset["end"] ||
            // otherwise it was a name and we get the end of the last word of the previous paragraph
            (
              selection.focusNode.parentElement?.parentElement
                ?.previousElementSibling?.lastElementChild as any
            )?.dataset["end"]
          : (selection.focusNode.parentElement?.previousElementSibling as any)
              ?.dataset["end"] || 0;

      const reverse = parseFloat(anchorStart) >= parseFloat(focusEnd);

      if (!reverse) {
        anchorStart &&
          focusEnd &&
          setSelectedText({
            start: parseFloat(anchorStart),
            end: parseFloat(focusEnd),
          });
      } else {
        const anchorEnd =
          anchorNode.parentElement?.dataset["end"] ||
          (
            selection.anchorNode.parentElement?.parentElement
              ?.previousElementSibling?.lastElementChild as any
          )?.dataset["end"];

        const focusStart = getStartTimeFromFirstNode(
          focusNode,
          selection.focusOffset,
          true,
        );

        setSelectedText({
          start: parseFloat(focusStart),
          end: parseFloat(anchorEnd),
        });
      }
    }
    selection && selection.empty();
  };

  const getSpeakerName = (speakerNumber: number) => {
    if (!participants.response) return;
    return (
      participants.response.find(
        (participant) => participant.speaker == speakerNumber,
      )?.name || `Speaker ${speakerNumber}`
    );
  };
  if (
    !topicWithWords.loading &&
    topicWithWords.response &&
    participants.response
  ) {
    return (
      <Container
        onMouseUp={onMouseUp}
        max-h="100%"
        width="100%"
        overflow="scroll"
        maxW={{ lg: "container.md" }}
        {...chakraProps}
      >
        {topicWithWords.response.words_per_speaker?.map(
          (speakerWithWords, index) => (
            <Text key={index} className="mb-2 last:mb-0">
              <Box
                as="span"
                data-speaker={speakerWithWords.speaker}
                pt="1"
                fontWeight="semibold"
                bgColor={
                  selectedText == speakerWithWords.speaker ? "yellow.200" : ""
                }
              >
                {getSpeakerName(speakerWithWords.speaker)}&nbsp;:&nbsp;
              </Box>
              {speakerWithWords.words.map((word, index) => (
                <Box
                  as="span"
                  data-start={word.start}
                  data-end={word.end}
                  key={index}
                  pt="1"
                  bgColor={
                    selectedTextIsTimeSlice(selectedText) &&
                    selectedText.start <= word.start &&
                    selectedText.end >= word.end
                      ? "yellow.200"
                      : ""
                  }
                >
                  {word.text}
                </Box>
              ))}
            </Text>
          ),
        )}
      </Container>
    );
  }
  if (topicWithWords.loading || participants.loading)
    return <Spinner size="xl" margin="auto" />;
  return null;
};

export default topicWords;
