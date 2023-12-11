import { SetStateAction, useCallback, useEffect, useState } from "react";
import WaveformLoading from "../../waveformLoading";
import { UseParticipants } from "../../useParticipants";
import { Participant } from "../../../../api";

type Word = {
  end: number;
  speaker: number;
  start: number;
  text: string;
};

type WordBySpeaker = { speaker: number; words: Word[] }[];

// TODO shortcuts
// TODO fix key (using indexes might act up, not sure as we don't re-order per say)

type TopicWordsProps = {
  setSelectedTime: SetStateAction<any>;
  selectedTime: any;
  setTopicTime: SetStateAction<any>;
  stateSelectedSpeaker: any;
  participants: UseParticipants;
  topicWithWords: any;
};

const topicWords = ({
  setSelectedTime,
  selectedTime,
  setTopicTime,
  stateSelectedSpeaker,
  participants,
  topicWithWords,
}: TopicWordsProps) => {
  const [wordsBySpeaker, setWordsBySpeaker] = useState<WordBySpeaker>();
  const [selectedSpeaker, setSelectedSpeaker] = stateSelectedSpeaker;

  useEffect(() => {
    if (topicWithWords.loading) {
      setWordsBySpeaker([]);
      setSelectedTime(undefined);
      console.log("unsetting topic changed");
    }
  }, [topicWithWords.loading]);

  useEffect(() => {
    if (!topicWithWords.loading && !topicWithWords.error) {
      const wordsFlat = topicWithWords.response.words as Word[];
      const wordsSorted = wordsFlat.reduce((acc, curr) => {
        if (acc.length > 0 && acc[acc.length - 1].speaker == curr.speaker) {
          acc[acc.length - 1].words.push(curr);
          return acc;
        } else {
          acc?.push({ speaker: curr.speaker, words: [curr] });
          return acc;
        }
      }, [] as WordBySpeaker);
      setWordsBySpeaker(wordsSorted);
      setTopicTime({
        start: wordsFlat.at(0)?.start,
        end: wordsFlat.at(wordsFlat.length - 1)?.end,
      });
    }
  }, [topicWithWords.response]);

  const onMouseUp = (e) => {
    let selection = window.getSelection();
    if (
      selection &&
      selection.anchorNode &&
      selection.focusNode &&
      selection.anchorNode == selection.focusNode &&
      selection.anchorOffset == selection.focusOffset
    ) {
      setSelectedTime(undefined);
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
        setSelectedSpeaker(focusNode.parentElement?.dataset["speaker"]);
        setSelectedTime(undefined);
        selection.empty();
        console.log("Unset Time : selected Speaker");
        return;
      }

      const anchorStart = anchorIsWord
        ? anchorNode.parentElement?.dataset["start"]
        : (selection.anchorNode.parentElement?.nextElementSibling as any)
            ?.dataset["start"];
      const focusEnd =
        selection.focusNode.parentElement?.dataset["end"] ||
        (
          selection.focusNode.parentElement?.parentElement
            ?.previousElementSibling?.lastElementChild as any
        )?.dataset["end"];
      const reverse = parseFloat(anchorStart) > parseFloat(focusEnd);

      if (!reverse) {
        setSelectedTime({ start: anchorStart, end: focusEnd });
        console.log("setting right");
      } else {
        const anchorEnd = anchorIsWord
          ? anchorNode.parentElement?.dataset["end"]
          : (selection.anchorNode.parentElement?.nextElementSibling as any)
              ?.dataset["end"];
        const focusStart =
          selection.focusNode.parentElement?.dataset["start"] ||
          (
            selection.focusNode.parentElement?.parentElement
              ?.previousElementSibling?.lastElementChild as any
          )?.dataset["start"];
        setSelectedTime({ start: focusStart, end: anchorEnd });
        console.log("setting reverse");
      }
      setSelectedSpeaker();
      selection.empty();
    }
  };

  const getSpeakerName = (speakerNumber: number) => {
    if (!participants.response) return;
    return (
      (participants.response as Participant[]).find(
        (participant) => participant.speaker == speakerNumber,
      )?.name || `Speaker ${speakerNumber}`
    );
  };

  if (!topicWithWords.loading && wordsBySpeaker && participants.response) {
    return (
      <div onMouseUp={onMouseUp} onBlur={(e) => console.log(e)}>
        {wordsBySpeaker?.map((speakerWithWords, index) => (
          <p key={index}>
            <span
              data-speaker={speakerWithWords.speaker}
              className={
                selectedSpeaker == speakerWithWords.speaker
                  ? "bg-yellow-200"
                  : ""
              }
            >
              {getSpeakerName(speakerWithWords.speaker)}&nbsp;:&nbsp;
            </span>
            {speakerWithWords.words.map((word, index) => (
              <span
                data-start={word.start}
                data-end={word.end}
                key={index}
                className={
                  selectedTime &&
                  selectedTime.start <= word.start &&
                  selectedTime.end >= word.end
                    ? "bg-yellow-200"
                    : ""
                }
              >
                {word.text}
              </span>
            ))}
          </p>
        ))}
      </div>
    );
  }
  if (topicWithWords.loading) return <WaveformLoading />;
  if (topicWithWords.error) return <p>error</p>;
  return null;
};

export default topicWords;
