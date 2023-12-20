import { Dispatch, SetStateAction, useEffect } from "react";
import WaveformLoading from "../../waveformLoading";
import { UseParticipants } from "../../useParticipants";
import { UseTopicWithWords } from "../../useTopicWithWords";
import { TimeSlice, selectedTextIsTimeSlice } from "./types";

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
}: TopicWordsProps) => {
  const [selectedText, setSelectedText] = stateSelectedText;

  useEffect(() => {
    if (topicWithWords.loading && selectedTextIsTimeSlice(selectedText)) {
      setSelectedText(undefined);
    }
  }, [topicWithWords.loading]);

  const getStartTimeFromFirstNode = (node, offset, reverse) => {
    // if the first element is a word
    return node.parentElement?.dataset["start"]
      ? // but after of the word (like on the blank space right of the word)
        node.textContent?.length == offset
        ? // if next element is a word, we need the start of it
          (node.parentElement?.nextElementSibling as any)?.dataset?.["start"] ||
          // otherwise we get the start of the first word of the next paragraph
          (
            node.parentElement?.parentElement?.nextElementSibling
              ?.childNodes[1] as any
          )?.dataset?.["start"] ||
          (reverse ? 0 : 99)
        : // otherwise it's just somewhere in the word and we get the start of the word
          node.parentElement?.dataset["start"]
      : // otherwise selection start is on a name and we get the start of the next word
        (node.parentElement?.nextElementSibling as any)?.dataset["start"];
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
        console.log("Unset Time : selected Speaker");
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
        setSelectedText({
          start: parseFloat(anchorStart),
          end: parseFloat(focusEnd),
        });
        console.log("setting right");
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
        console.log("setting reverse");
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
      <div onMouseUp={onMouseUp} className="p-5 h-full w-full overflow-scroll">
        {topicWithWords.response.wordsPerSpeaker.map(
          (speakerWithWords, index) => (
            <p key={index} className="mb-2 last:mb-0">
              <span
                data-speaker={speakerWithWords.speaker}
                className={`
                  font-semibold ${
                    selectedText == speakerWithWords.speaker
                      ? "bg-yellow-200"
                      : ""
                  }`}
              >
                {getSpeakerName(speakerWithWords.speaker)}&nbsp;:&nbsp;
              </span>
              {speakerWithWords.words.map((word, index) => (
                <span
                  data-start={word.start}
                  data-end={word.end}
                  key={index}
                  className={
                    selectedTextIsTimeSlice(selectedText) &&
                    selectedText.start <= word.start &&
                    selectedText.end >= word.end
                      ? "bg-yellow-200"
                      : ""
                  }
                >
                  {word.text}
                </span>
              ))}
            </p>
          ),
        )}
      </div>
    );
  }
  if (topicWithWords.loading || participants.loading)
    return <WaveformLoading />;
  if (topicWithWords.error || participants.error) return <p>error</p>;
  return null;
};

export default topicWords;
