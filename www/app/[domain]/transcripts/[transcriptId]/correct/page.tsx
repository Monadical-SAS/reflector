"use client";
import { useEffect, useState } from "react";
import useTranscript from "../../useTranscript";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";
import TopicPlayer from "./topicPlayer";
import useParticipants from "../../useParticipants";
import useTopicWithWords from "../../useTopicWithWords";
import ParticipantList from "./participantList";
import { GetTranscriptTopic } from "../../../../api";

export type TranscriptCorrect = {
  params: {
    transcriptId: string;
  };
};

export type TimeSlice = {
  start: number;
  end: number;
};

export type SelectedText = number | TimeSlice | undefined;

export function selectedTextIsSpeaker(
  selectedText: SelectedText,
): selectedText is number {
  return typeof selectedText == "number";
}
export function selectedTextIsTimeSlice(
  selectedText: SelectedText,
): selectedText is TimeSlice {
  return (
    typeof (selectedText as any)?.start == "number" &&
    typeof (selectedText as any)?.end == "number"
  );
}

export default function TranscriptCorrect(details: TranscriptCorrect) {
  const transcriptId = details.params.transcriptId;
  const stateCurrentTopic = useState<GetTranscriptTopic>();
  const [currentTopic, _sct] = stateCurrentTopic;
  const topicWithWords = useTopicWithWords(currentTopic?.id, transcriptId);

  const [topicTime, setTopicTime] = useState<TimeSlice>();
  const participants = useParticipants(transcriptId);
  const stateSelectedText = useState<SelectedText>();
  const [selectedText, _sst] = stateSelectedText;

  useEffect(() => {
    if (currentTopic) {
      setTopicTime({
        start: currentTopic.timestamp,
        end: currentTopic.timestamp + currentTopic.duration,
      });
    } else {
      setTopicTime(undefined);
    }
  }, [currentTopic]);

  return (
    <div className="h-full grid grid-cols-2 gap-4">
      <div className="flex flex-col h-full">
        <TopicHeader
          stateCurrentTopic={stateCurrentTopic}
          transcriptId={transcriptId}
        />
        <TopicWords
          stateSelectedText={stateSelectedText}
          participants={participants}
          topicWithWords={topicWithWords}
        />
      </div>
      <div className="flex flex-col justify-stretch">
        <TopicPlayer
          transcriptId={transcriptId}
          selectedTime={
            selectedTextIsTimeSlice(selectedText) ? selectedText : undefined
          }
          topicTime={topicTime}
        />
        <ParticipantList
          {...{
            transcriptId,
            participants,
            topicWithWords,
            stateSelectedText,
          }}
        />
      </div>
    </div>
  );
}
