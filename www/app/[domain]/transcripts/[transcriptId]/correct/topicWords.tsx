import { useCallback, useEffect, useState } from "react";
import useTopicWithWords from "../../useTopicWithWords";
import WaveformLoading from "../../waveformLoading";

type Word = {
  end: number;
  speaker: number;
  start: number;
  text: string;
};

type WordBySpeaker = { speaker: number; words: Word[] }[];

// TODO fix selection reversed
// TODO shortcuts
// TODO fix key (using indexes might act up, not sure as we don't re-order per say)

const topicWords = ({
  setSelectedTime,
  currentTopic,
  transcriptId,
  setTopicTime,
  stateSelectedSpeaker,
  participants,
}) => {
  const topicWithWords = useTopicWithWords(currentTopic, transcriptId);
  const [wordsBySpeaker, setWordsBySpeaker] = useState<WordBySpeaker>();
  const [selectedSpeaker, setSelectedSpeaker] = stateSelectedSpeaker;

  useEffect(() => {
    if (topicWithWords.loading) {
      setWordsBySpeaker([]);
      setSelectedTime(undefined);
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

  useEffect(() => {
    document.onmouseup = (e) => {
      let selection = window.getSelection();
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
        const correctedAnchor = anchorIsWord
          ? anchorNode
          : anchorNode.parentNode?.firstChild;
        const anchorOffset = anchorIsWord ? 1 : 0;
        const focusNode = selection.focusNode;
        const focusIsWord = !!selection.focusNode.parentElement?.dataset["end"];
        const correctedfocus = focusIsWord
          ? focusNode
          : focusNode.parentNode?.lastChild;
        const focusOffset = focusIsWord
          ? focusNode.textContent?.length
          : focusNode.parentNode?.lastChild?.textContent?.length;

        if (
          correctedAnchor &&
          anchorOffset !== undefined &&
          correctedfocus &&
          focusOffset !== undefined
        ) {
          selection.setBaseAndExtent(
            correctedAnchor,
            anchorOffset,
            correctedfocus,
            focusOffset,
          );

          if (
            !anchorIsWord &&
            !focusIsWord &&
            anchorNode.parentElement == focusNode.parentElement
          ) {
            console.log(focusNode.parentElement?.dataset);
            setSelectedSpeaker(focusNode.parentElement?.dataset["speaker"]);
            setSelectedTime(undefined);
          } else {
            setSelectedSpeaker(undefined);
            setSelectedTime({
              start:
                selection.anchorNode.parentElement?.dataset["start"] ||
                (selection.anchorNode.parentElement?.nextElementSibling as any)
                  ?.dataset["start"] ||
                0,
              end:
                selection.focusNode.parentElement?.dataset["end"] ||
                (
                  selection.focusNode.parentElement?.parentElement
                    ?.previousElementSibling?.lastElementChild as any
                )?.dataset ||
                0,
            });
          }
        }
      }
      if (
        selection &&
        selection.anchorNode &&
        selection.focusNode &&
        selection.anchorNode == selection.focusNode &&
        selection.anchorOffset == selection.focusOffset
      ) {
        setSelectedTime(undefined);
      }
    };
  }, []);

  const getSpeakerName = useCallback(
    (speakerNumber: number) => {
      return (
        participants.response.find((participant) => {
          participant.speaker == speakerNumber;
        }) || `Speaker ${speakerNumber}`
      );
    },
    [participants],
  );

  if (!topicWithWords.loading && wordsBySpeaker && participants) {
    return (
      <div>
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
              <span data-start={word.start} data-end={word.end} key={index}>
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
